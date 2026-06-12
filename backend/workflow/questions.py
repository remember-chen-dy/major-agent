"""10 个预设问题配置 + 节点工厂函数

每个问题节点不调用 LLM，所有引导语为预设文案。
节点仅生成 AIMessage 并返回，不做 interrupt() 调用 ——
中断由 graph.compile() 的 interrupt_after 统一处理。
答案存储由 assessment_service 通过 Command.update 完成。
"""
from langchain_core.messages import AIMessage
from workflow.state import AssessmentState

# ============================================================
# 问题配置注册表
# ============================================================

QUESTION_CONFIG = {
    "q1_score": {
        "guidance": "同学你好！咱们先从最基本的信息开始：你的模考或高考预估分数是多少分？全省排名（位次）大概在什么范围？",
        "interaction": {
            "type": "form",
            "fields": [
                {"id": "score", "label": "预估分数", "type": "number", "placeholder": "如 620"},
                {"id": "rank", "label": "全省位次", "type": "number", "placeholder": "如 8500"},
            ],
        },
        "next": "q2_subject",
    },
    "q2_subject": {
        "guidance": "接下来了解一下你的选科情况。你选了哪些科目？可多选哦。",
        "interaction": {
            "type": "tag_multi_select",
            "tags": ["物理", "化学", "生物", "历史", "地理", "政治"],
            "min_select": 1,
            "max_select": 6,
        },
        "next": "q3_city",
    },
    "q3_city": {
        "guidance": "关于大学所在的城市，你心里有偏好吗？",
        "interaction": {
            "type": "button_select",
            "options": [
                {"value": "一线", "label": "一线城市（北上广深）——机会多、节奏快"},
                {"value": "离家近", "label": "离家近就好——不想跑太远"},
                {"value": "偏远也行", "label": "偏远一点也行——好学校在哪我就去哪"},
            ],
        },
        "next": "q4_energy",
    },
    "q4_energy": {
        "guidance": "在社交场合里，你的能量来源更偏向哪一种？",
        "interaction": {
            "type": "button_select",
            "options": [
                {"value": "E", "label": "🟢 社交充能（E）——和人待在一起让我活力满满"},
                {"value": "I", "label": "🔵 独处充电（I）——独处/小圈子才是我恢复精力的方式"},
            ],
        },
        "next": "q5_cognition",
    },
    "q5_cognition": {
        "guidance": "思考问题的时候，你的风格更接近哪一种？",
        "interaction": {
            "type": "slider",
            "min": 0,
            "max": 100,
            "left_label": "步步为营——我喜欢按部就班，扎实走好每一步",
            "right_label": "天马行空——我喜欢发散跳跃，在脑海里自由驰骋",
        },
        "next": "q6_flow",
    },
    "q6_flow": {
        "guidance": "做什么事情会让你忘记时间、完全沉浸其中？可多选，也可以补充你自己的答案。",
        "interaction": {
            "type": "tag_multi_select",
            "tags": [
                "破解逻辑谜题 / 做数学题",
                "写东西（文章、日记、诗歌）",
                "画画、设计、视觉创作",
                "拆解组装、动手修理",
                "倾听朋友的烦恼并给出建议",
                "钻研游戏机制、研究攻略",
            ],
            "allow_custom": True,
            "custom_placeholder": "其他让我心流的事...",
        },
        "next": "q7_pressure",
    },
    "q7_pressure": {
        "guidance": "面对压力的时候，你更倾向于哪种状态？",
        "interaction": {
            "type": "slider",
            "min": 0,
            "max": 100,
            "left_label": "乘风破浪——压力越大我越兴奋，喜欢挑战",
            "right_label": "岁月静好——我想要安稳、低压力的学习与生活节奏",
        },
        "next": "q8_family",
    },
    "q8_family": {
        "guidance": "你的家庭在升学这件事上能提供什么样的资源？",
        "interaction": {
            "type": "button_select",
            "options": [
                {"value": "resource_high", "label": "家里有相关资源 / 行业人脉"},
                {"value": "resource_mid", "label": "有一点人脉，但不多"},
                {"value": "resource_low", "label": "全靠自己拼"},
            ],
        },
        "next": "q9_taboos",
    },
    "q9_taboos": {
        "guidance": "有没有你绝对不想碰的领域或场景？勾选所有让你心生抗拒的。不选也没关系~",
        "interaction": {
            "type": "tag_multi_select",
            "tags": [
                "见血 / 临床 / 手术",
                "大量数学 / 抽象推导",
                "枯燥重复的实验室工作",
                "疯狂背书 / 记忆密集型",
                "公开演讲 / 频繁汇报",
                "长时间盯代码",
            ],
            "min_select": 0,
        },
        "next": "q10_expect",
    },
    "q10_expect": {
        "guidance": "最后一个问题，也是最重要的——你希望大学四年最终带给你什么？三选一。",
        "interaction": {
            "type": "button_select",
            "options": [
                {"value": "skill", "label": "💪 过硬的职业技能——毕业就能找到好工作"},
                {"value": "vision", "label": "🌍 广阔的视野和思维——看到更大的世界"},
                {"value": "diploma", "label": "🎓 安稳的文凭——平稳度过四年，拿到学历"},
            ],
        },
        "next": "planner",
    },
}

# ============================================================
# 问题节点工厂
# ============================================================


def make_question_node(step_name: str):
    """创建问题节点函数

    节点仅负责生成带 interaction 配置的 AIMessage 并返回。
    不调用 interrupt() —— 中断由 interrupt_after 处理。
    不存储答案 —— 答案由 assessment_service 通过 Command.update 写入 state。

    Args:
        step_name: 问题 ID，如 "q1_score"

    Returns:
        async node function
    """
    config = QUESTION_CONFIG[step_name]

    async def node(state: AssessmentState) -> dict:
        guidance = config["guidance"]
        interaction = config["interaction"]

        ai_msg = AIMessage(
            content=guidance,
            additional_kwargs={"interaction": interaction, "question_id": step_name},
        )
    
        return {
            "messages": [ai_msg],
            "current_step": step_name,
        }

    # 设置节点名称方便调试
    node.__name__ = step_name
    return node


# ============================================================
# 问题顺序（供 service 层推进 current_step 使用）
# ============================================================

QUESTION_ORDER = [
    "q1_score", "q2_subject", "q3_city", "q4_energy", "q5_cognition",
    "q6_flow", "q7_pressure", "q8_family", "q9_taboos", "q10_expect",
]


def get_next_step(current_step: str) -> str:
    """获取下一个步骤名称"""
    try:
        idx = QUESTION_ORDER.index(current_step)
        if idx < len(QUESTION_ORDER) - 1:
            return QUESTION_ORDER[idx + 1]
    except ValueError:
        pass
    return "planner"  # 最后一题之后进入 ReWOO 管线
