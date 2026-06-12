"""LangGraph 工作流状态定义"""
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AssessmentState(TypedDict):
    """测评全流程状态

    messages:        标准消息列表（LangGraph 内置 reducer 合并）
    current_step:    当前节点标识 (q1_score / q2_subject / ... / final_agent / done)
    answers:         用户答案字典 {question_id: answer_value}
    planner_output:  Planner 输出的工具调用计划
    tool_results:    工具执行结果字典 {tool_name: result_str}
    report:          最终 Markdown 报告文本
    report_pdf_url:  PDF 下载链接
    is_complete:     测评是否已完成
    """
    messages: Annotated[list, add_messages]
    current_step: str
    answers: dict
    planner_output: list
    tool_results: dict
    report: str
    report_pdf_url: str
    is_complete: bool
