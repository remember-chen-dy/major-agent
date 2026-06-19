"""ReWOO 三节点报告生成器 —— Planner/Executor/Solver

使用 4 个独立工具分析考生画像，生成志愿规划报告。
"""
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial

from duckduckgo_search import DDGS
from langchain_core.messages import AIMessage

from config.llm import get_llm
from workflow.state import AssessmentState

# 全局线程池，用于并发执行同步工具函数
_tool_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="rewoo_tool_")


# ============================================================
# 4 个分析工具
# ============================================================


def _score_band_analyzer(score: int, rank: int) -> str:
    """根据分数和位次分析院校层次（优先使用网络搜索获取最新数据）"""
    try:
        year = datetime.now().year
        query = f"{year}高考{score}分 位次{rank} 能报考什么大学 冲稳保策略,以及这个院校对应的专业"

        # 使用新版 DuckDuckGo API
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=5))
            search_result = "\n".join([r.get("body", "") for r in search_results])

        llm = get_llm()
        band_analysis = llm.invoke(
            f"根据以下搜索结果，为一位高考{score}分、全省位次{rank}名的考生"
            f"整理出冲稳保建议，分别从冲刺、稳妥、保底三个角度分析，"
            f"输出包含院校名称和专业方向的冲稳保表格：\n\n{search_result}"
        )
        return f"""## 成绩定位分析（基于 {year} 年网络数据）
            
                - **分数**：{score} 分
                - **位次**：全省第 {rank} 名

                {band_analysis.content}
                 """
    except Exception:
        # 搜索失败时使用降级方案
        if score >= 650:
            band = "可冲刺 C9 联盟院校（清华、北大、复旦、浙大等顶尖985）"
        elif score >= 600:
            band = "适合报考中上游 985 和顶尖 211 院校"
        elif score >= 550:
            band = "适合报考普通 211 院校和实力较强的一本院校"
        elif score >= 500:
            band = "适合报考普通一本院校和优质二本院校"
        elif score >= 450:
            band = "适合报考普通二本院校"
        else:
            band = "适合报考民办本科和优质专科院校"

        rush = [f"{max(score + 20, 600)}-{score + 30}分段院校（冲刺）"]
        steady = [f"{score - 10}-{score + 10}分段院校（稳妥）"]
        safe = [f"{score - 30}-{score - 10}分段院校（保底）"]

        return f"""## 成绩定位分析

            - **分数**：{score} 分
            - **位次**：全省第 {rank} 名
            - **院校层次**：{band}

            ### 冲稳保建议
            | 策略 | 分数区间 | 说明 |
            |------|----------|------|
            | 🚀 冲刺 | {rush[0]} | 可以搏一搏的院校 |
            | ✅ 稳妥 | {steady[0]} | 匹配度最高的院校 |
            | 🛡️ 保底 | {safe[0]} | 确保有学上的院校 |
            """


def _major_matcher(
    subjects: list[str],
    energy: str,
    cognition: str,
    flow_tags: list[str],
    pressure: str,
    expectation: str,
    taboos: list[str],
) -> str:
    """根据多维画像匹配专业方向"""
    # 选科判断
    is_science = any(s in subjects for s in ["物理", "化学", "生物"])
    is_arts = any(s in subjects for s in ["历史", "地理", "政治"])

    results = []

    if is_science and "盯代码" not in str(taboos):
        results.append({
            "major": "计算机科学与技术 / 软件工程",
            "score": 95,
            "reason": "理科基础扎实，就业前景广阔，薪资水平领先",
        })
        results.append({
            "major": "人工智能 / 数据科学",
            "score": 90,
            "reason": "前沿交叉学科，适合有数学和逻辑优势的理科生",
        })

    if is_science and "见血" not in str(taboos):
        results.append({
            "major": "临床医学 / 口腔医学",
            "score": 85,
            "reason": "社会地位高、越老越吃香，但学制较长需耐心",
        })

    if is_science:
        results.append({
            "major": "电子信息工程 / 通信工程",
            "score": 82,
            "reason": "国家战略方向，芯片和通信行业人才缺口大",
        })

    if is_arts and "疯狂背书" not in str(taboos):
        results.append({
            "major": "法学 / 知识产权",
            "score": 85,
            "reason": "文科高薪方向之一，逻辑思维要求高",
        })
        results.append({
            "major": "汉语言文学 / 新闻传播",
            "score": 78,
            "reason": "内容行业持续增长，表达能力强是核心优势",
        })

    if expectation == "skill":
        results.append({
            "major": "金融学 / 金融科技",
            "score": 80,
            "reason": "文理兼收，技能导向明确，行业薪酬可观",
        })

    if "写东西" in str(flow_tags) or "画画" in str(flow_tags):
        results.append({
            "major": "数字媒体艺术 / 设计学类",
            "score": 75,
            "reason": "符合你的创作心流偏好，创意产业前景良好",
        })

    # 按匹配度排序取 Top 5
    results.sort(key=lambda x: x["score"], reverse=True)
    top5 = results[:5]

    lines = ["## 专业方向建议\n"]
    lines.append("| 排名 | 推荐专业 | 匹配度 | 推荐理由 |")
    lines.append("|:---:|------|:---:|------|")
    for i, r in enumerate(top5, 1):
        lines.append(f"| {i} | **{r['major']}** | {r['score']}% | {r['reason']} |")

    return "\n".join(lines)


def _taboo_filter(taboos: list[str], matched_majors: list[str]) -> str:
    """基于雷区过滤不适合的专业并提供提醒"""
    taboo_warnings = {
        "见血": "⚠️ 你对临床/手术场景有抗拒，建议排除临床医学、护理学等需要大量临床实践的专业",
        "大量数学": "⚠️ 你对高强度数学推导有顾虑，建议慎重考虑数学、物理、统计学等纯理专业",
        "枯燥实验": "⚠️ 你对重复性实验工作不感兴趣，建议避开基础化学、生物技术等实验密集型专业",
        "疯狂背书": "⚠️ 你对大量记忆有排斥，建议慎重选择法学、中医学等需要大量背诵的专业",
        "公开演讲": "⚠️ 你对公开汇报有压力，建议考虑对表达能力要求不那么极端的技术型专业",
        "盯代码": "⚠️ 你不想长时间盯代码，建议避开纯软件开发方向，可关注产品经理、技术管理等相关方向",
    }

    lines = ["## 避坑提醒\n"]
    for taboo in taboos:
        for keyword, warning in taboo_warnings.items():
            if keyword in str(taboo):
                lines.append(warning)
                break
        else:
            lines.append(f"⚠️ 雷区「{taboo}」——建议在选专业时主动避开相关领域")

    if not taboos:
        lines.append("✅ 你未标记任何绝对雷区，选择面较广。但仍建议结合自身实际体验进一步了解各专业的日常学习内容。")

    return "\n".join(lines)


def _city_advisor(city_pref: str, score_band: str, family_resource: str) -> str:
    """城市与院校选择建议"""
    city_map = {
        "一线": "一线城市（北京/上海/广州/深圳）院校资源丰富，实习和就业机会多，但生活成本较高。建议高分考生冲刺一线 985/211，中分考生可关注一线城市的普通一本或优质二本。",
        "离家近": "优先考虑省内高校。省内院校对本省考生通常有招生计划倾斜和分数优惠，是一个性价比很高的选择。同时关注邻省优质院校作为补充。",
        "偏远也行": "你的选择面很广！可以考虑：东北的哈工大、吉大；西北的西交大、兰大；西南的川大、电子科大；华中的武大、华科——这些学校虽然地理位置不在一线，但学术实力非常强。",
    }

    family_map = {
        "resource_high": "家庭有行业资源，可重点关注与家族资源匹配的专业方向和院校。",
        "resource_mid": "家庭有一定人脉，可在目标行业中寻求信息和建议，辅助决策。",
        "resource_low": "全靠自己拼搏，建议重点关注就业率高、起薪好的专业，以及奖学金覆盖好的院校。",
    }

    lines = ["## 城市与院校分析\n"]

    for key, advice in city_map.items():
        if key in str(city_pref):
            lines.append(f"### 城市偏好：{city_pref}")
            lines.append(advice)
            break

    lines.append(f"\n### 家庭资源情况")
    for key, advice in family_map.items():
        if key in str(family_resource):
            lines.append(advice)
            break

    return "\n".join(lines)


# ============================================================
# 用户画像构建
# ============================================================


def _build_user_profile(answers: dict) -> dict:
    """从原始答案构建结构化用户画像"""
    profile = {}

    q1 = answers.get("q1_score", {}) or {}
    profile["score"] = q1.get("score", "未知")
    profile["rank"] = q1.get("rank", "未知")

    profile["subjects"] = answers.get("q2_subject", [])
    profile["province"] = answers.get("q3_province", "未知")
    profile["city_pref"] = answers.get("q4_city", "未知")
    profile["energy"] = answers.get("q5_energy", "未知")
    profile["mbti"] = answers.get("q6_mbti", "未知")
    profile["cognition"] = answers.get("q7_cognition", "未知")
    profile["flow_tags"] = answers.get("q8_flow", [])
    profile["pressure"] = answers.get("q9_pressure", "未知")
    profile["family_resource"] = answers.get("q10_family", "未知")
    profile["taboos"] = answers.get("q11_taboos", [])
    profile["expectation"] = answers.get("q12_expect", "未知")

    return profile


# ============================================================
# ReWOO 三节点
# ============================================================


async def planner_node(state: AssessmentState) -> dict:
    """Planner —— 第 1 次 LLM 调用：分析用户画像，规划工具调用顺序"""
    llm = get_llm()
    answers = state.get("answers", {})
    user_profile = _build_user_profile(answers)

    planner_prompt = f"""你是一位高考志愿规划专家。根据以下考生的10项测评结果，规划需要调用的分析工具及其参数。

## 考生画像
{json.dumps(user_profile, ensure_ascii=False, indent=2)}

## 可用工具
1. score_band_analyzer(score: int, rank: int) — 分析分数位次对应的院校层次
2. major_matcher(subjects, energy, cognition, flow_tags, pressure, expectation, taboos) — 匹配专业方向
3. taboo_filter(taboos, matched_majors) — 基于雷区过滤不适合的专业
4. city_advisor(city_pref, score_band, family_resource) — 城市与院校选择建议

请输出一个 JSON 数组，按合理的调用顺序列出需要执行的工具：
```json
[{{"tool": "score_band_analyzer", "args": {{"score": {user_profile['score']}, "rank": {user_profile['rank']}}}}}, ...]
```

只输出 JSON 数组，不要任何额外文字。
"""

    response = await llm.ainvoke(planner_prompt)
    content = response.content.strip()

    # 解析 JSON
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        planner_output = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: 按默认顺序执行
        planner_output = [
            {"tool": "score_band_analyzer", "args": {"score": user_profile.get("score", 600), "rank": user_profile.get("rank", 10000)}},
            {"tool": "major_matcher", "args": {
                "subjects": user_profile.get("subjects", []),
                "energy": str(user_profile.get("energy", "")),
                "cognition": str(user_profile.get("cognition", "")),
                "flow_tags": user_profile.get("flow_tags", []),
                "pressure": str(user_profile.get("pressure", "")),
                "expectation": str(user_profile.get("expectation", "")),
                "taboos": user_profile.get("taboos", []),
            }},
            {"tool": "taboo_filter", "args": {
                "taboos": user_profile.get("taboos", []),
                "matched_majors": ["计算机科学与技术", "软件工程", "人工智能", "临床医学", "法学"],
            }},
            {"tool": "city_advisor", "args": {
                "city_pref": str(user_profile.get("city_pref", "")),
                "score_band": "中高分" if user_profile.get("score", 0) > 550 else "中低分",
                "family_resource": str(user_profile.get("family_resource", "")),
            }},
        ]

    return {
        "planner_output": planner_output,
        "current_step": "executor",
    }


async def executor_node(state: AssessmentState) -> dict:
    """Executor —— 使用线程池并发执行工具调用，不调 LLM"""
    planner_output = state.get("planner_output", [])

    tool_map = {
        "score_band_analyzer": _score_band_analyzer,
        "major_matcher": _major_matcher,
        "taboo_filter": _taboo_filter,
        "city_advisor": _city_advisor,
    }

    if not planner_output:
        return {"tool_results": {}, "current_step": "solver"}

    loop = asyncio.get_event_loop()

    async def execute_tool(call: dict):
        tool_name = call.get("tool", "")
        args = call.get("args", {})

        if tool_name not in tool_map:
            return tool_name, {"error": f"未知工具: {tool_name}"}

        try:
            # 使用 partial 包装函数和参数
            func = partial(tool_map[tool_name], **args)
            # 在线程池中执行，避免阻塞事件循环
            result = await loop.run_in_executor(_tool_executor, func)
            return tool_name, result
        except Exception as e:
            return tool_name, {"error": f"工具执行失败: {e}"}

    # 并发执行所有工具
    tasks = [execute_tool(call) for call in planner_output]
    results = await asyncio.gather(*tasks)

    # 组装结果
    tool_results = {}
    for tool_name, result in results:
        tool_results[tool_name] = result

    return {
        "tool_results": tool_results,
        "current_step": "solver",
    }


async def solver_node(state: AssessmentState) -> dict:
    """Solver —— 第 2 次 LLM 调用：综合所有信息，生成志愿规划报告"""
    llm = get_llm()
    answers = state.get("answers", {})
    user_profile = _build_user_profile(answers)
    tool_results = state.get("tool_results", {})

    solver_prompt = f"""
        你是一位温暖而专业的高考志愿规划师。根据以下信息，为考生撰写一份完整的志愿规划报告。

        ## 考生画像
        {json.dumps(user_profile, ensure_ascii=False, indent=2)}

        ## 工具分析结果
        {json.dumps(tool_results, ensure_ascii=False, indent=2)}

        请用 Markdown 格式输出报告，包含以下章节：

        # 🎓 高考志愿规划报告

        ## 一、成绩定位
        基于分数和位次，分析考生所处竞争层次，给出总体判断。

        ## 二、冲稳保院校推荐
        用表格列出冲刺、稳妥、保底三个层次的推荐院校和专业方向（每个层次 2-3 所），需要提醒是当年最新数据，并给出查询网站名称相关。

        ## 三、专业方向建议
        推荐 3-5 个最匹配的专业，说明理由和就业前景。

        ## 四、专业四年后就业前景分析
        分析专业四年后就业前景，包括就业率、薪资范围、工作环境等。

        ## 五、避坑提醒
        基于雷区标签和考生特点，提醒需要避开的方向和常见误区。

        ## 六、城市与院校选择策略
        结合城市偏好和考生特点，提醒需要避开的方向和常见误区。

        ## 七、下一步行动
        给出具体的下一步行动建议，例如「建议去 B 站搜这两个专业的大三课表看看，感受一下实际学什么」，这里可以详细些。

        ## 八、个性化结语
        温暖鼓励的结尾，让考生感到被理解和支持。

        ### 语言要求
        - 亲切、专业、有温度
        - 像一位关心学生的老师在认真给出建议
        - 不要过于绝对化的表述
        - 对于分数偏低的同学给予鼓励，对分数较高的同学给予肯定
        - 对于专业方向建议，要根据考生的个人特点和目标，给出符合其需求的专业建议
        - 对于避坑提醒，要根据考生的个人特点和目标，给出符合其需求的避坑建议
        - 使用「建议」「可以考虑」「值得关注」等措辞

        ### 补充要求
        - **结合用户画像的具体细节**：提到心流时刻、性格倾向时，引用用户原话或具体标签，例如「你提到喜欢拆解组装东西，这正是机械/电子类专业的核心乐趣」，让用户感觉被真正理解
        - **避免制造焦虑**：不使用「天坑专业」「毕业即失业」等恐慌性表述，改从「这个方向目前竞争激烈，建议同步关注 XX 作为备选」的角度
        - **承认不确定性**：对于预测性内容（就业趋势、行业前景），加「基于当前趋势」「未来可能有变化」等限定词，不把话说死
        - **口语化但不过分随意**：可以偶尔用「其实」「说实话」「帮你捋一捋」这类词，但避免「绝绝子」「码住」「家人们」等网络用语
        - **逻辑链条完整**：推荐一个专业时，必须说清「因为你的 XX 特质 + XX 外部条件 → 所以推荐 XX」，让用户理解推导过程而非被动接受结论
        - **报告长度控制在 1500-2500 字**：太短显得敷衍，太长没人看完。冲稳保表格不计入字数
"""

    response = await llm.ainvoke(solver_prompt)
    report = response.content.strip()

    return {
        "report": report,
        "messages": [AIMessage(content=report)],
        "current_step": "markdown_done",
    }
