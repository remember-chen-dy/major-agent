"""报告完成节点。

当前产品阶段直接展示 Markdown 报告，不再生成 PDF，也不上传对象存储。
保留节点名称是为了不改 LangGraph 结构。
"""
from workflow.state import AssessmentState


async def pdf_generator_node(state: AssessmentState) -> dict:
    """结束报告流程，返回 Markdown 报告完成状态。"""
    return {
        "report_pdf_url": "",
        "report_file_key": "",
        "current_step": "done",
        "is_complete": True,
    }
