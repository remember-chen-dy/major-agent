"""12 个预设问题配置 + 节点工厂函数

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
        "guidance": "同学你好呀！👋 很高兴见到你。我是你的高考志愿规划顾问，你可以叫我张老师。我知道现在这个阶段，面对几百个专业和上千所院校，很多同学都觉得特别迷茫——这很正常，不用焦虑，咱们一步步来。",
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
        "guidance": "语数英为必考科目，请再从以下科目中选择 3 门作为选考科目。",
        "interaction": {
            "type": "tag_multi_select",
            "tags": ["物理", "化学", "生物", "历史", "地理", "政治"],
            "min_select": 3,
            "max_select": 3,
            "preset_subjects": ["语文", "数学", "英语"],
        },
        "next": "q3_province",
    },
    "q3_province": {
        "guidance": "你来自哪个省份（高考所在省）？不同省份的录取政策和竞争情况差别很大哦。",
        "interaction": {
            "type": "button_select",
            "options": [
                {"value": "北京", "label": "北京"},
                {"value": "天津", "label": "天津"},
                {"value": "河北", "label": "河北"},
                {"value": "山西", "label": "山西"},
                {"value": "内蒙古", "label": "内蒙古"},
                {"value": "辽宁", "label": "辽宁"},
                {"value": "吉林", "label": "吉林"},
                {"value": "黑龙江", "label": "黑龙江"},
                {"value": "上海", "label": "上海"},
                {"value": "江苏", "label": "江苏"},
                {"value": "浙江", "label": "浙江"},
                {"value": "安徽", "label": "安徽"},
                {"value": "福建", "label": "福建"},
                {"value": "江西", "label": "江西"},
                {"value": "山东", "label": "山东"},
                {"value": "河南", "label": "河南"},
                {"value": "湖北", "label": "湖北"},
                {"value": "湖南", "label": "湖南"},
                {"value": "广东", "label": "广东"},
                {"value": "广西", "label": "广西"},
                {"value": "海南", "label": "海南"},
                {"value": "重庆", "label": "重庆"},
                {"value": "四川", "label": "四川"},
                {"value": "贵州", "label": "贵州"},
                {"value": "云南", "label": "云南"},
                {"value": "西藏", "label": "西藏"},
                {"value": "陕西", "label": "陕西"},
                {"value": "甘肃", "label": "甘肃"},
                {"value": "青海", "label": "青海"},
                {"value": "宁夏", "label": "宁夏"},
                {"value": "新疆", "label": "新疆"},
            ],
        },
        "next": "q4_city",
    },
    "q4_city": {
        "guidance": "关于大学所在的城市，你心里有偏好吗？",
        "interaction": {
            "type": "button_select",
            "options": [
                {"value": "一线", "label": "一线城市（北上广深）——机会多、节奏快"},
                {"value": "离家近", "label": "离家近就好——不想跑太远"},
                {"value": "偏远也行", "label": "偏远一点也行——好学校在哪我就去哪"},
            ],
        },
        "next": "q5_energy",
    },
    "q5_energy": {
        "guidance": "在社交场合里，你的能量来源更偏向哪一种？",
        "interaction": {
            "type": "button_select",
            "options": [
                {"value": "E", "label": "🟢 社交充能（E）——和人待在一起让我活力满满"},
                {"value": "I", "label": "🔵 独处充电（I）——独处/小圈子才是我恢复精力的方式"},
            ],
        },
        "next": "q6_mbti",
    },
    "q6_mbti": {
        "guidance": "你了解自己的 MBTI 类型吗？选一个最符合你的。不确定的话可以凭直觉选~",
        "interaction": {
            "type": "button_select",
            "searchable": True,
            "options": [
                {"value": "INTJ", "label": "INTJ 建筑师——独立、战略、果断"},
                {"value": "INTP", "label": "INTP 逻辑学家——创新、好奇、爱分析"},
                {"value": "ENTJ", "label": "ENTJ 指挥官——大胆、有远见、领导力"},
                {"value": "ENTP", "label": "ENTP 辩论家——机智、好奇、爱挑战"},
                {"value": "INFJ", "label": "INFJ 提倡者——安静、有洞察、理想主义"},
                {"value": "INFP", "label": "INFP 调停者——诗意、善良、追求意义"},
                {"value": "ENFJ", "label": "ENFJ 主人公——热情、利他、有魅力"},
                {"value": "ENFP", "label": "ENFP 竞选者——热情、创意、自由"},
                {"value": "ISTJ", "label": "ISTJ 物流师——务实、可靠、注重事实"},
                {"value": "ISFJ", "label": "ISFJ 守卫者——专注、温暖、守护"},
                {"value": "ESTJ", "label": "ESTJ 总经理——高效、管理、执行力"},
                {"value": "ESFJ", "label": "ESFJ 执政官——关心、善于合作、热心"},
                {"value": "ISTP", "label": "ISTP 鉴赏家——大胆、实操、爱动手"},
                {"value": "ISFP", "label": "ISFP 探险家——灵活、迷人、探索者"},
                {"value": "ESTP", "label": "ESTP 企业家——精力旺盛、敏锐、享受冒险"},
                {"value": "ESFP", "label": "ESFP 表演者——即兴、外向、活在当下"},
            ],
        },
        "next": "q7_cognition",
    },
    "q7_cognition": {
        "guidance": "思考问题的时候，你的风格更接近哪一种？",
        "interaction": {
            "type": "button_select",
            "options": [
                {"value": "step_by_step", "label": "步步为营——我喜欢按部就班，扎实走好每一步"},
                {"value": "free_association", "label": "天马行空——我喜欢发散跳跃，在脑海里自由驰骋"},
                {"value": "balanced", "label": "两者之间——根据情况灵活切换"}
            ]
        },
        "next": "q8_flow"
    },
    "q8_flow": {
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
        "next": "q9_pressure",
    },
        "q9_pressure": {
            "guidance": "面对压力的时候，你更倾向于哪种状态？",
            "interaction": {
                "type": "button_select",
                "options": [
                    {"value": "thrive", "label": "乘风破浪——压力越大我越兴奋，喜欢挑战"},
                    {"value": "calm", "label": "岁月静好——我想要安稳、低压力的学习与生活节奏"},
                    {"value": "moderate", "label": "适中有度——能接受一定压力，但不喜欢过度"}
                ]
            },
            "next": "q10_family"
        },
    "q10_family": {
        "guidance": "你的家庭在升学这件事上能提供什么样的资源？",
        "interaction": {
            "type": "button_select",
            "options": [
                {"value": "resource_high", "label": "家里有相关资源 / 行业人脉"},
                {"value": "resource_mid", "label": "有一点人脉，但不多"},
                {"value": "resource_low", "label": "全靠自己拼"},
            ],
        },
        "next": "q11_taboos",
    },
    "q11_taboos": {
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
        "next": "q12_expect",
    },
    "q12_expect": {
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
    "q1_score", "q2_subject", "q3_province", "q4_city", "q5_energy", "q6_mbti",
    "q7_cognition", "q8_flow", "q9_pressure", "q10_family", "q11_taboos", "q12_expect",
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
