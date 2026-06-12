"""PDF 生成节点 —— 将 Markdown 报告转换为 PDF"""
import os
from workflow.state import AssessmentState


async def pdf_generator_node(state: AssessmentState) -> dict:
    """将 Markdown 报告转为 PDF 文件，返回下载链接"""
    report_md = state.get("report", "")

    if not report_md:
        return {
            "report_pdf_url": "",
            "current_step": "done",
            "is_complete": True,
        }

    try:
        import markdown
        from weasyprint import HTML

        # Markdown → HTML
        md = markdown.Markdown(extensions=["tables", "fenced_code", "codehilite"])
        html_body = md.convert(report_md)

        html_doc = f"""<!DOCTYPE html>
                <html lang="zh-CN">
                <head>
                <meta charset="utf-8">
                <style>
                body {{ font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; max-width: 800px; margin: 0 auto; padding: 40px; color: #333; line-height: 1.8; }}
                h1 {{ text-align: center; color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: 12px; }}
                h2 {{ color: #16213e; margin-top: 32px; border-left: 4px solid #e94560; padding-left: 12px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 10px 14px; text-align: left; }}
                th {{ background-color: #f0f0f0; font-weight: bold; }}
                tr:nth-child(even) {{ background-color: #fafafa; }}
                blockquote {{ border-left: 4px solid #e94560; padding-left: 16px; color: #555; margin: 16px 0; }}
                </style>
                </head>
                <body>{html_body}</body>
                </html>
            """

        # 确保 reports 目录存在
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "reports")
        os.makedirs(reports_dir, exist_ok=True)

        session_id = state.get("current_step", "unknown")
        pdf_path = os.path.join(reports_dir, f"{session_id}.pdf")

        HTML(string=html_doc).write_pdf(pdf_path)

        pdf_url = f"/static/reports/{session_id}.pdf"

        return {
            "report_pdf_url": pdf_url,
            "current_step": "done",
            "is_complete": True,
        }

    except ImportError as e:
        # weasyprint 未正确安装时的降级处理
        return {
            "report_pdf_url": f"data:text/markdown;base64,{report_md}",
            "current_step": "done",
            "is_complete": True,
        }
    except Exception as e:
        return {
            "report_pdf_url": "",
            "report": report_md,
            "current_step": "done",
            "is_complete": True,
        }
