"""测评业务逻辑层 —— LangGraph 图驱动，interrupt_after + Command.update 模式

每个问题节点后通过 interrupt_after 中断，答案通过 Command.update 写入 state。
"""
import uuid
from typing import Optional

from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage

from workflow import graph as wf_graph
from workflow.questions import get_next_step

# 问题顺序列表
QUESTION_ORDER = [
    "q1_score", "q2_subject", "q3_city", "q4_energy", "q5_cognition",
    "q6_flow", "q7_pressure", "q8_family", "q9_taboos", "q10_expect",
]


class AssessmentService:
    """测评服务类 —— 封装 LangGraph 图的 invoke / resume 操作"""

    # ================================================================
    # Session Creation
    # ================================================================

    @staticmethod
    async def create_session() -> tuple[str, dict]:
        """创建新会话，返回 session_id + 第一个问题的引导语和交互配置。

        图从入口节点 q1_score 开始执行，运行到 interrupt_after 自动暂停。

        Returns:
            (session_id, question_data_dict)
        """
        session_id = str(uuid.uuid4())[:8]
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}

        # 空状态启动，图会运行到 q1_score 节点后的 interrupt_after 暂停
        initial_state = {"current_step": "start", "answers": {}}
        result = await wf_graph.assessment_graph.ainvoke(initial_state, config=config)

        question_data = _extract_question_from_state(result)
        return session_id, question_data

    # ================================================================
    # Chat (Answer Submission)
    # ================================================================

    @staticmethod
    async def chat(session_id: str, answer) -> dict:
        """接收用户答案，通过 Command.update 写入 sta   te 并恢复图执行。

        图会从当前中断点继续，运行到下一个问题节点的 interrupt_after 暂停。
        如果是最后一个问题（q10），则一路跑到 END，返回最终报告。

        Args:
            session_id: 会话 ID（即 thread_id）
            answer: 用户提交的答案（dict / str / list / int 均可）

        Returns:
            dict: 包含 messages + current_step，或 report + is_complete
        """
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}

        # 检查当前状态
        current_state = await wf_graph.assessment_graph.aget_state(config)
        if not current_state or not current_state.values:
            return {"error": "会话不存在", "status": "not_found"}

        step = current_state.values.get("current_step", "")

        # 已完成
        if step == "done" or current_state.values.get("is_complete"):
            return {
                "current_step": "done",
                "is_complete": True,
                "report": current_state.values.get("report", ""),
                "report_pdf_url": current_state.values.get("report_pdf_url", ""),
            }

        # 构建完整 answers dict（保留旧答案 + 新答案）
        current_answers = dict(current_state.values.get("answers", {}))
        current_answers[step] = answer

        # 确定下一个 step
        next_step = get_next_step(step)

        # 通过 Command.update 写入答案并继续执行
        cmd = Command(
            resume=None,
            update={
                "answers": current_answers,
                "current_step": next_step,
            },
        )
        result = await wf_graph.assessment_graph.ainvoke(cmd, config=config)

        new_step = result.get("current_step", "")

        # 检查是否已完成（q10 回答后一路跑到 END）
        if new_step == "done" or result.get("is_complete"):
            return {
                "current_step": "done",
                "is_complete": True,
                "report": result.get("report", ""),
                "report_pdf_url": result.get("report_pdf_url", ""),
            }

        # 仍在问题阶段 —— 提取当前问题数据
        if new_step in QUESTION_ORDER:
            return _extract_question_from_state(result)

        # Fallback：可能处于 ReWOO 中间步骤
        return {
            "current_step": new_step,
            "is_complete": False,
        }
    
    # Results
    # ================================================================

    @staticmethod
    async def get_results(session_id: str) -> dict:
        """获取会话的最终报告（从 graph state 快照中读取）。"""
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}
        state = await wf_graph.assessment_graph.aget_state(config)
        if not state or not state.values:
            return {"error": "会话不存在"}

        return {
            "report": state.values.get("report", ""),
            "report_pdf_url": state.values.get("report_pdf_url", ""),
            "answers": state.values.get("answers", {}),
            "is_complete": state.values.get("is_complete", False),
        }


# ================================================================
# Helpers
# ================================================================


def _extract_question_from_state(state: dict) -> dict:
    """从图状态中提取当前问题的引导语和交互配置。

    从 messages 中倒序查找最后一条带 interaction 配置的 AIMessage，
    返回前端约定的响应格式：
        {
            "messages": [{"role": "ai", "content": "...", "interaction": {...}}],
            "current_step": "q1_score",
            "is_complete": false
        }
    """
    messages = state.get("messages", [])

    # 倒序遍历 messages，找到最后一条带 interaction 配置的 AIMessage
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

    # Fallback：无 interaction 配置时
    return {
        "messages": [],
        "current_step": state.get("current_step", ""),
        "is_complete": False,
    }
