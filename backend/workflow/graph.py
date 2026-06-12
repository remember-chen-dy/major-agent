"""LangGraph 测评工作流 —— 10 题独立节点 → ReWOO 报告生成

图结构（线性链）：
    START → q1_score → q2_subject → ... → q10_expect
          → planner → executor → solver → pdf_generator → END

- 每个问题节点后设置 interrupt_after，暂停等待前端提交答案
- ReWOO 管线（planner/executor/solver/pdf_generator）无中断，一路跑到底
- 答案由 assessment_service 通过 Command(resume=None, update={...}) 写入 state
- 使用 AsyncSqliteSaver checkpointer 持久化会话状态
"""
import aiosqlite

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from workflow.state import AssessmentState
from workflow.questions import make_question_node, QUESTION_ORDER
from workflow.final_agent import planner_node, executor_node, solver_node
from workflow.pdf_generator import pdf_generator_node


async def init_assessment_graph() -> StateGraph:
    """异步初始化编译测评 StateGraph

    手动管理 aiosqlite 连接和 AsyncSqliteSaver 的生命周期。
    """
    builder = StateGraph(AssessmentState)

    # ── 添加所有问题节点 ──
    for step_name in QUESTION_ORDER:
        node_fn = make_question_node(step_name)
        builder.add_node(step_name, node_fn)

    # ── 添加 ReWOO 管线节点 ──
    builder.add_node("planner", planner_node)
    builder.add_node("executor", executor_node)
    builder.add_node("solver", solver_node)
    builder.add_node("pdf_generator", pdf_generator_node)

    # ── 设置入口：从第一题开始 ──
    builder.set_entry_point(QUESTION_ORDER[0])

    # ── 线性边：q1→q2→...→q10 ──
    for i in range(len(QUESTION_ORDER) - 1):
        builder.add_edge(QUESTION_ORDER[i], QUESTION_ORDER[i + 1])

    # ── q10_expect → planner（进入 ReWOO 管线） ──
    builder.add_edge(QUESTION_ORDER[-1], "planner")

    # ── ReWOO 管线（无中断） ──
    builder.add_edge("planner", "executor")
    builder.add_edge("executor", "solver")
    builder.add_edge("solver", "pdf_generator")
    builder.add_edge("pdf_generator", END)

    # ── Checkpointer：手动管理连接 ──
    conn = await aiosqlite.connect("checkpoints.db")
    checkpointer = AsyncSqliteSaver(conn)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_after=QUESTION_ORDER,  # 每个问题节点后都中断
    )


# 全局编译后的图实例（在 main.py lifespan 中异步初始化后设置）
assessment_graph: StateGraph | None = None
