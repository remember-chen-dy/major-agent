"""报告生成服务。

使用 ReWOO 三节点流程生成 Markdown 报告。
"""
from datetime import datetime

from sqlalchemy import select, update

from config.database import async_session
from models.session import Session
from workflow.final_agent import planner_node, executor_node, solver_node, _build_user_profile


class ReportService:
    """报告生成服务"""

    @staticmethod
    async def generate_report(session_id: str, user_id: str, answers: dict):
        """后台生成 Markdown 报告（使用 ReWOO 流程）。"""
        try:
            async with async_session() as db:
                await db.execute(
                    update(Session)
                    .where(Session.id == session_id)
                    .values(report_status="generating", report_progress=35)
                )
                await db.commit()

            # 构建初始状态
            state = {
                "answers": answers or {},
                "planner_output": [],
                "tool_results": {},
                "report": "",
                "messages": [],
                "current_step": "planner",
            }

            # 执行 ReWOO 三节点流程
            planner_result = await planner_node(state)
            state.update(planner_result)

            executor_result = await executor_node(state)
            state.update(executor_result)

            solver_result = await solver_node(state)
            report = solver_result.get("report", "")

            async with async_session() as db:
                result = await db.execute(select(Session).where(Session.id == session_id))
                session = result.scalar_one_or_none()
                if not session:
                    return

                messages = session.messages or []
                messages.append({
                    "role": "ai",
                    "content": report,
                    "report": report,
                    "created_at": datetime.now().isoformat(),
                })

                session.messages = messages
                session.report_status = "completed"
                session.report_progress = 100
                session.report_url = ""
                session.report_file_key = ""
                await db.commit()

            print(f"✅ Markdown 报告生成完成: session={session_id}, user={user_id}")

        except Exception as e:
            print(f"❌ 报告生成失败: session={session_id}, error={e}")

            try:
                async with async_session() as db:
                    await db.execute(
                        update(Session)
                        .where(Session.id == session_id)
                        .values(
                            report_status="failed",
                            report_progress=0,
                        )
                    )
                    await db.commit()
            except Exception as update_error:
                print(f"更新失败状态时出错: {update_error}")
