"""测评业务逻辑层 —— LangGraph 图驱动，interrupt_after + Command.update 模式

每个问题节点后通过 interrupt_after 中断，答案通过 Command.update 写入 state。
最后一题回答后立即返回，ReWOO 报告生成管线在后台异步执行。
前端通过轮询 GET /session/{id}/results 获取报告。
"""
import asyncio
import uuid

from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from workflow import graph as wf_graph
from workflow.questions import get_next_step, QUESTION_CONFIG
from models.session import Session

# 问题顺序列表
QUESTION_ORDER = [
    "q1_score", "q2_subject", "q3_province", "q4_city", "q5_energy", "q6_mbti",
    "q7_cognition", "q8_flow", "q9_pressure", "q10_family", "q11_taboos", "q12_expect",
]


class AssessmentService:
    """测评服务类 —— 封装 LangGraph 图的 invoke / resume 操作"""

    # ================================================================
    # Session Creation
    # ================================================================

    @staticmethod
    async def create_session(db: AsyncSession, user_id: str, title: str = "新会话") -> tuple[str, dict]:
        """创建新会话，返回 session_id + 第一个问题的引导语和交互配置。

        Args:
            db: 数据库会话
            user_id: 用户 ID (字符串 UUID)
            title: 会话标题

        Returns:
            (session_id, first_question): 会话 ID 和第一个问题数据
        """
        from sqlalchemy.exc import IntegrityError

        # 生成数据库会话 ID 和 LangGraph thread_id
        session_uuid = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())[:8]

        # 直接从预设配置获取第一个问题（不走 LangGraph，避免图执行异常导致页面空白）
        first_step = QUESTION_ORDER[0]
        config = QUESTION_CONFIG[first_step]
        question_data = {
            "messages": [
                {
                    "role": "ai",
                    "content": config["guidance"],
                    "interaction": config["interaction"],
                }
            ],
            "current_step": first_step,
            "is_complete": False,
        }

        # 异步初始化 LangGraph（失败不影响主流程）
        try:
            initial_state = {
                "current_step": "start",
                "answers": {},
                "session_id": str(session_uuid),
                "user_id": user_id,
            }
            await wf_graph.assessment_graph.ainvoke(
                initial_state, config={"configurable": {"thread_id": thread_id}}
            )
        except Exception as e:
            print(f"[warn] LangGraph 初始化失败（不影响使用）: {e}")

        # 创建数据库会话记录
        db_session = Session(
            id=str(session_uuid),
            user_id=user_id,
            title=title,
            status="active",
            report_status="pending",
            report_progress=0,
            langgraph_thread_id=thread_id,
            messages=question_data.get("messages", []),
        )

        try:
            db.add(db_session)
            await db.commit()
            await db.refresh(db_session)
        except IntegrityError as e:
            await db.rollback()
            # 检查是否是外键约束违反
            if "foreign key constraint" in str(e.orig).lower():
                raise ValueError(f"用户 {user_id} 不存在，请先创建用户") from e
            raise

        # 返回数据库 session_id（前端使用）
        return str(db_session.id), question_data

    # ================================================================
    # Chat (Answer Submission)
    # ================================================================

    @staticmethod
    async def chat(db: AsyncSession, session_id: str, answer) -> dict:
        """接收用户答案，通过 Command.update 写入 state 并恢复图执行。

        如果是最后一题（q12），立即返回 processing 状态，
        ReWOO 管线在后台异步执行，前端轮询获取结果。

        Args:
            db: 数据库会话
            session_id: 数据库会话 ID
            answer: 用户答案

        Returns:
            对话结果字典
        """
        # 从数据库加载会话
        result = await db.execute(select(Session).where(Session.id == session_id))
        db_session = result.scalar_one_or_none()

        if not db_session:
            return {"error": "会话不存在", "status": "not_found"}

        if db_session.report_status == "failed":
            return {
                "current_step": "failed",
                "is_failed": True,
                "is_complete": False,
                "is_generating": False,
                "report_status": "failed",
                "report_progress": db_session.report_progress,
                "error": "当前会话报告生成失败，请重新测评",
                "status": "failed",
            }

        if db_session.report_status == "generating":
            return {
                "current_step": "processing",
                "is_generating": True,
                "is_complete": False,
                "report_status": db_session.report_status,
                "report_progress": db_session.report_progress,
            }

        if db_session.report_status == "completed":
            return await AssessmentService.get_results(db=db, session_id=session_id)

        thread_id = db_session.langgraph_thread_id
        if not thread_id:
            return {"error": "无效的 LangGraph 线程", "status": "invalid"}

        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

        # 获取当前 LangGraph 状态
        try:
            current_state = await wf_graph.assessment_graph.aget_state(config)
        except Exception as exc:
            print(f"读取 LangGraph 状态失败: session={session_id}, error={exc}")
            return {"error": "会话状态异常，请重新测评", "status": "invalid"}

        if not current_state or not current_state.values:
            return {"error": "会话状态不存在，请重新测评", "status": "invalid"}

        step = current_state.values.get("current_step", "")
        if step not in QUESTION_ORDER and step not in {"processing", "done", "planner", "executor", "solver", "markdown_done"}:
            return {"error": "会话状态异常，请重新测评", "status": "invalid"}

        if step == "done" or current_state.values.get("is_complete"):
            return await AssessmentService.get_results(db=db, session_id=session_id)

        if step == "processing":
            return {
                "current_step": "processing",
                "is_generating": True,
                "is_complete": False,
                "report_status": "generating",
                "report_progress": db_session.report_progress,
            }

        # 添加用户消息到数据库。已生成/生成中状态会在上面提前返回，避免重复追加最后一题答案。
        user_msg = {
            "role": "user",
            "content": str(answer),
            "user_input": answer,
        }
        current_messages = db_session.messages or []
        current_messages.append(user_msg)
        db_session.messages = current_messages

        # 构建完整 answers dict
        current_answers = dict(current_state.values.get("answers", {}))
        current_answers[step] = answer

        next_step = get_next_step(step)

        cmd = Command(
            resume=None,
            update={
                "answers": current_answers,
                "current_step": next_step,
                "session_id": str(db_session.id),
                "user_id": str(db_session.user_id),
            },
        )

        # ── 最后一题：立即返回，后台执行完整管线 ──
        if step == "q12_expect":
            # 后台执行：resume q12 → planner → executor → solver → markdown 完成态 → END
            db_session.report_status = "generating"
            db_session.report_progress = 10
            asyncio.create_task(_run_report_pipeline(db_session.id, thread_id, cmd))

            await db.commit()
            return {
                "current_step": "processing",
                "is_generating": True,
                "is_complete": False,
                "report_status": "generating",
                "report_progress": 10,
            }

        # ── 非最后一题：正常执行到下一个 interrupt_after ──
        result = await wf_graph.assessment_graph.ainvoke(cmd, config=config)

        new_step = result.get("current_step", "")

        if new_step == "done" or result.get("is_complete"):
            # 添加 AI 报告消息到数据库
            ai_msg = {
                "role": "ai",
                "content": result.get("report", ""),
                "report": result.get("report", ""),
                "report_pdf_url": "",
            }
            current_messages.append(ai_msg)
            db_session.messages = current_messages
            db_session.report_status = "completed"
            db_session.report_progress = 100
            db_session.report_url = ""
            db_session.report_file_key = ""
            await db.commit()
            return {
                "current_step": "done",
                "is_complete": True,
                "report": result.get("report", ""),
                "report_url": "",
                "report_pdf_url": "",
            }

        if new_step in QUESTION_ORDER:
            # 提取下一个问题
            question_data = _extract_question_from_state(result)
            # 添加 AI 问题消息到数据库
            ai_msgs = question_data.get("messages", [])
            current_messages.extend(ai_msgs)
            db_session.messages = current_messages
            await db.commit()
            return question_data

        await db.commit()
        return {"current_step": new_step, "is_complete": False}

    # ================================================================
    # Results
    # ================================================================

    @staticmethod
    async def get_results(db: AsyncSession, session_id: str) -> dict:
        """获取会话的最终报告（从数据库读取）。

        Args:
            db: 数据库会话
            session_id: 数据库会话 ID

        Returns:
            包含报告、答案和完成状态的字典
        """
        # 从数据库加载会话
        result = await db.execute(select(Session).where(Session.id == session_id))
        db_session = result.scalar_one_or_none()

        if not db_session:
            return {"error": "会话不存在"}

        # 从 messages 中提取最后一条报告
        messages = db_session.messages or []
        report = _extract_report_from_messages(messages)

        # 兼容历史数据：有些会话曾被写成 completed，但 messages 没有报告。
        # 先尝试从 LangGraph checkpoint 恢复；恢复不到就改成 failed，避免前端展示空报告。
        if db_session.report_status == "completed" and not report:
            report = await _recover_report_from_graph(db_session)
            if report:
                messages.append({
                    "role": "ai",
                    "content": report,
                    "report": report,
                    "report_pdf_url": "",
                })
                db_session.messages = messages
                db_session.report_url = ""
                db_session.report_file_key = ""
                await db.commit()
            else:
                db_session.report_status = "failed"
                db_session.report_progress = 0
                db_session.report_url = ""
                db_session.report_file_key = ""
                await db.commit()

        is_complete = db_session.report_status == "completed"

        return {
            "report": report,
            "report_pdf_url": "",
            "report_url": db_session.report_url or "",
            "report_status": db_session.report_status,
            "report_progress": db_session.report_progress,
            "messages": messages,
            "is_complete": is_complete,
            "is_generating": db_session.report_status == "generating",
            "is_failed": db_session.report_status == "failed",
        }


# ================================================================
# 后台报告生成
# ================================================================


async def _run_report_pipeline(session_id: str, thread_id: str, cmd: Command):
    """后台执行报告生成管线

    从 q12 中断点恢复，一路执行：
    q12_expect → planner → executor → solver → markdown 完成态 → END
    完成后 state 中会写入 report 和 is_complete 标志。

    Args:
        db_session: 数据库会话对象
        thread_id: LangGraph 线程 ID
        cmd: LangGraph Command
    """
    from config.database import async_session

    async def update_progress(progress: int) -> None:
        async with async_session() as db:
            session_result = await db.execute(select(Session).where(Session.id == session_id))
            session = session_result.scalar_one_or_none()
            if session:
                session.report_status = "generating"
                session.report_progress = progress
                await db.commit()

    try:
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        await update_progress(35)
        result = await wf_graph.assessment_graph.ainvoke(cmd, config=config)
        await update_progress(90)
        print(f"✅ 报告生成完成: session={session_id}")

        # 更新数据库：保存报告到 messages 和 report 字段
        async with async_session() as db:
            # 重新加载会话
            session_result = await db.execute(select(Session).where(Session.id == session_id))
            updated_session = session_result.scalar_one_or_none()
            if updated_session:
                # 添加报告消息
                current_messages = updated_session.messages or []
                ai_msg = {
                    "role": "ai",
                    "content": result.get("report", ""),
                    "report": result.get("report", ""),
                    "report_pdf_url": "",
                }
                current_messages.append(ai_msg)
                updated_session.messages = current_messages
                updated_session.report_status = "completed"
                updated_session.report_progress = 100
                updated_session.report_url = ""
                updated_session.report_file_key = ""
                await db.commit()
    except Exception as e:
        print(f"❌ 报告生成失败: session={session_id}, error={e}")
        # 更新失败状态
        async with async_session() as db:
            session_result = await db.execute(select(Session).where(Session.id == session_id))
            failed_session = session_result.scalar_one_or_none()
            if failed_session:
                failed_session.report_status = "failed"
                failed_session.report_progress = 0
                await db.commit()


# ================================================================
# Helpers
# ================================================================


def _extract_question_from_state(state: dict) -> dict:
    """从图状态中提取当前问题的引导语和交互配置。"""
    messages = state.get("messages", [])

    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            extra = msg.additional_kwargs if hasattr(msg, "additional_kwargs") else {}
            if extra and "interaction" in extra:
                return {
                    "messages": [
                        {
                            "role": "ai",
                            "content": msg.content,
                            "interaction": extra["interaction"],
                        }
                    ],
                    "current_step": extra.get("question_id", state.get("current_step", "")),
                    "is_complete": False,
                }

    return {
        "messages": [],
        "current_step": state.get("current_step", ""),
        "is_complete": False,
    }


def _extract_report_from_messages(messages: list) -> str:
    """从消息历史中提取最后一份非空报告。"""
    for msg in reversed(messages):
        if not isinstance(msg, dict) or msg.get("role") != "ai":
            continue

        report = (msg.get("report") or "").strip()
        if report:
            return report

        content = (msg.get("content") or "").strip()
        if msg.get("current_step") == "done" and content:
            return content

    return ""


async def _recover_report_from_graph(db_session: Session) -> str:
    """从 LangGraph checkpoint 尝试恢复报告。"""
    if not db_session.langgraph_thread_id:
        return ""

    try:
        config: RunnableConfig = {"configurable": {"thread_id": db_session.langgraph_thread_id}}
        graph_state = await wf_graph.assessment_graph.aget_state(config)
    except Exception as exc:
        print(f"恢复报告失败: session={db_session.id}, error={exc}")
        return ""

    values = graph_state.values if graph_state else {}
    report = (values.get("report") or "").strip()
    if report:
        return report

    messages = values.get("messages", [])
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        if isinstance(content, str) and content.strip().startswith("#"):
            return content.strip()

    return ""
