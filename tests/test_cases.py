"""评估测试用例（100+ 测试用例）

覆盖三种查询类型：
- structured: 结构化查询（SQL）
- semantic: 语义查询（RAG）
- hybrid: 混合查询（SQL + RAG）

每个测试用例包含：
- question: 用户问题
- expected_route: 期望路由（structured/semantic/hybrid）
- keywords: 期望包含的关键信息
- difficulty: 难度（easy/medium/hard）
"""

# ==================== 结构化查询（SQL）- 35 个 ====================

STRUCTURED_QUERIES = [
    # 基础统计（10 个）
    {
        "question": "有多少个UP主？",
        "expected_route": "structured",
        "keywords": ["UP主", "数量", "统计"],
        "difficulty": "easy",
    },
    {
        "question": "总共采集了多少个视频？",
        "expected_route": "structured",
        "keywords": ["视频", "总数", "数量"],
        "difficulty": "easy",
    },
    {
        "question": "哪个分类的视频最多？",
        "expected_route": "structured",
        "keywords": ["分类", "最多", "视频"],
        "difficulty": "easy",
    },
    {
        "question": "最近一周新增了多少视频？",
        "expected_route": "structured",
        "keywords": ["最近", "一周", "新增"],
        "difficulty": "easy",
    },
    {
        "question": "播放量最高的视频是哪个？",
        "expected_route": "structured",
        "keywords": ["播放量", "最高", "视频"],
        "difficulty": "easy",
    },
    {
        "question": "点赞数最多的视频是什么？",
        "expected_route": "structured",
        "keywords": ["点赞", "最多", "视频"],
        "difficulty": "easy",
    },
    {
        "question": "平均每个视频有多少弹幕？",
        "expected_route": "structured",
        "keywords": ["平均", "弹幕", "数量"],
        "difficulty": "easy",
    },
    {
        "question": "有多少个视频的播放量超过10万？",
        "expected_route": "structured",
        "keywords": ["播放量", "10万", "超过"],
        "difficulty": "easy",
    },
    {
        "question": "哪个UP主的视频平均播放量最高？",
        "expected_route": "structured",
        "keywords": ["UP主", "平均播放量", "最高"],
        "difficulty": "medium",
    },
    {
        "question": "最近一个月哪个分类的视频增长最快？",
        "expected_route": "structured",
        "keywords": ["最近", "一个月", "增长", "最快"],
        "difficulty": "medium",
    },

    # 条件筛选（10 个）
    {
        "question": "桃姐有哪些视频？",
        "expected_route": "structured",
        "keywords": ["桃姐", "视频", "列表"],
        "difficulty": "easy",
    },
    {
        "question": "显示所有情感类的视频",
        "expected_route": "structured",
        "keywords": ["情感", "分类", "视频"],
        "difficulty": "easy",
    },
    {
        "question": "播放量超过5万的视频有哪些？",
        "expected_route": "structured",
        "keywords": ["播放量", "5万", "超过"],
        "difficulty": "easy",
    },
    {
        "question": "最近发布的10个视频是什么？",
        "expected_route": "structured",
        "keywords": ["最近", "发布", "10个"],
        "difficulty": "easy",
    },
    {
        "question": "哪个UP主的视频最少？",
        "expected_route": "structured",
        "keywords": ["UP主", "视频", "最少"],
        "difficulty": "easy",
    },
    {
        "question": "显示弹幕数最多的前5个视频",
        "expected_route": "structured",
        "keywords": ["弹幕", "最多", "前5"],
        "difficulty": "easy",
    },
    {
        "question": "收藏数超过1000的视频有哪些？",
        "expected_route": "structured",
        "keywords": ["收藏", "1000", "超过"],
        "difficulty": "easy",
    },
    {
        "question": "哪个分类的平均播放量最高？",
        "expected_route": "structured",
        "keywords": ["分类", "平均播放量", "最高"],
        "difficulty": "medium",
    },
    {
        "question": "最近一周哪个UP主发布的视频最多？",
        "expected_route": "structured",
        "keywords": ["最近", "一周", "UP主", "发布", "最多"],
        "difficulty": "medium",
    },
    {
        "question": "播放量和点赞数都超过1万的视频有哪些？",
        "expected_route": "structured",
        "keywords": ["播放量", "点赞", "1万", "超过"],
        "difficulty": "medium",
    },

    # 复杂查询（15 个）
    {
        "question": "每个UP主有多少个视频？按数量排序",
        "expected_route": "structured",
        "keywords": ["UP主", "视频数量", "排序"],
        "difficulty": "medium",
    },
    {
        "question": "每个分类的平均播放量是多少？",
        "expected_route": "structured",
        "keywords": ["分类", "平均播放量", "统计"],
        "difficulty": "medium",
    },
    {
        "question": "哪些UP主最近一个月没有发布新视频？",
        "expected_route": "structured",
        "keywords": ["UP主", "最近", "一个月", "没有发布"],
        "difficulty": "medium",
    },
    {
        "question": "播放量最高的前10个视频分别属于哪个分类？",
        "expected_route": "structured",
        "keywords": ["播放量", "前10", "分类"],
        "difficulty": "medium",
    },
    {
        "question": "哪个UP主的视频平均点赞数最高？",
        "expected_route": "structured",
        "keywords": ["UP主", "平均点赞", "最高"],
        "difficulty": "medium",
    },
    {
        "question": "最近发布的视频中，播放量最高的是哪个？",
        "expected_route": "structured",
        "keywords": ["最近", "发布", "播放量", "最高"],
        "difficulty": "medium",
    },
    {
        "question": "每个分类有多少个视频？按数量降序排列",
        "expected_route": "structured",
        "keywords": ["分类", "视频数量", "降序"],
        "difficulty": "medium",
    },
    {
        "question": "哪些视频的弹幕数超过平均弹幕数的两倍？",
        "expected_route": "structured",
        "keywords": ["弹幕", "平均", "两倍", "超过"],
        "difficulty": "hard",
    },
    {
        "question": "最近一周发布的视频中，哪个分类的视频最多？",
        "expected_route": "structured",
        "keywords": ["最近", "一周", "分类", "最多"],
        "difficulty": "medium",
    },
    {
        "question": "播放量超过平均播放量的视频有哪些？",
        "expected_route": "structured",
        "keywords": ["播放量", "平均", "超过"],
        "difficulty": "medium",
    },
    {
        "question": "哪个UP主的视频总播放量最高？",
        "expected_route": "structured",
        "keywords": ["UP主", "总播放量", "最高"],
        "difficulty": "medium",
    },
    {
        "question": "每个UP主的平均视频时长是多少？",
        "expected_route": "structured",
        "keywords": ["UP主", "平均", "视频时长"],
        "difficulty": "medium",
    },
    {
        "question": "最近一个月内，播放量增长最快的视频是哪个？",
        "expected_route": "structured",
        "keywords": ["最近", "一个月", "增长", "最快"],
        "difficulty": "hard",
    },
    {
        "question": "哪些视频同时具有高播放量和高点赞数？",
        "expected_route": "structured",
        "keywords": ["高播放量", "高点赞", "同时"],
        "difficulty": "hard",
    },
    {
        "question": "每个分类的视频总数、平均播放量、总播放量分别是多少？",
        "expected_route": "structured",
        "keywords": ["分类", "总数", "平均播放量", "总播放量"],
        "difficulty": "hard",
    },
]

# ==================== 语义查询（RAG）- 35 个 ====================

SEMANTIC_QUERIES = [
    # 内容理解（10 个）
    {
        "question": "桃姐最近讲了什么情感话题？",
        "expected_route": "semantic",
        "keywords": ["桃姐", "情感", "话题"],
        "difficulty": "easy",
    },
    {
        "question": "有哪些关于人际关系的建议？",
        "expected_route": "semantic",
        "keywords": ["人际关系", "建议"],
        "difficulty": "easy",
    },
    {
        "question": "视频中提到了哪些沟通技巧？",
        "expected_route": "semantic",
        "keywords": ["沟通", "技巧"],
        "difficulty": "easy",
    },
    {
        "question": "有什么关于婚姻的观点？",
        "expected_route": "semantic",
        "keywords": ["婚姻", "观点"],
        "difficulty": "easy",
    },
    {
        "question": "视频里讨论了哪些家庭问题？",
        "expected_route": "semantic",
        "keywords": ["家庭", "问题"],
        "difficulty": "easy",
    },
    {
        "question": "有哪些关于自我成长的建议？",
        "expected_route": "semantic",
        "keywords": ["自我成长", "建议"],
        "difficulty": "easy",
    },
    {
        "question": "视频中提到了哪些情感故事？",
        "expected_route": "semantic",
        "keywords": ["情感", "故事"],
        "difficulty": "easy",
    },
    {
        "question": "有什么关于恋爱的建议？",
        "expected_route": "semantic",
        "keywords": ["恋爱", "建议"],
        "difficulty": "easy",
    },
    {
        "question": "视频里讨论了哪些心理问题？",
        "expected_route": "semantic",
        "keywords": ["心理", "问题"],
        "difficulty": "easy",
    },
    {
        "question": "有哪些关于人生感悟的内容？",
        "expected_route": "semantic",
        "keywords": ["人生", "感悟"],
        "difficulty": "easy",
    },

    # 主题检索（10 个）
    {
        "question": "最近有什么关于职场的话题？",
        "expected_route": "semantic",
        "keywords": ["职场", "话题"],
        "difficulty": "easy",
    },
    {
        "question": "视频中提到了哪些关于友情的观点？",
        "expected_route": "semantic",
        "keywords": ["友情", "观点"],
        "difficulty": "easy",
    },
    {
        "question": "有什么关于父母关系的讨论？",
        "expected_route": "semantic",
        "keywords": ["父母", "关系"],
        "difficulty": "easy",
    },
    {
        "question": "视频里提到了哪些情绪管理的方法？",
        "expected_route": "semantic",
        "keywords": ["情绪管理", "方法"],
        "difficulty": "medium",
    },
    {
        "question": "有哪些关于亲密关系的建议？",
        "expected_route": "semantic",
        "keywords": ["亲密关系", "建议"],
        "difficulty": "easy",
    },
    {
        "question": "视频中讨论了哪些社会现象？",
        "expected_route": "semantic",
        "keywords": ["社会", "现象"],
        "difficulty": "easy",
    },
    {
        "question": "有什么关于自我认知的内容？",
        "expected_route": "semantic",
        "keywords": ["自我认知"],
        "difficulty": "easy",
    },
    {
        "question": "视频里提到了哪些关于幸福感的讨论？",
        "expected_route": "semantic",
        "keywords": ["幸福感", "讨论"],
        "difficulty": "easy",
    },
    {
        "question": "有哪些关于压力管理的建议？",
        "expected_route": "semantic",
        "keywords": ["压力管理", "建议"],
        "difficulty": "easy",
    },
    {
        "question": "视频中提到了哪些关于成长的观点？",
        "expected_route": "semantic",
        "keywords": ["成长", "观点"],
        "difficulty": "easy",
    },

    # 深度理解（15 个）
    {
        "question": "桃姐对现代婚姻有什么看法？",
        "expected_route": "semantic",
        "keywords": ["桃姐", "现代婚姻", "看法"],
        "difficulty": "medium",
    },
    {
        "question": "视频中关于沟通有哪些具体的建议？",
        "expected_route": "semantic",
        "keywords": ["沟通", "具体建议"],
        "difficulty": "medium",
    },
    {
        "question": "有哪些关于处理冲突的方法？",
        "expected_route": "semantic",
        "keywords": ["冲突", "方法"],
        "difficulty": "medium",
    },
    {
        "question": "视频里提到了哪些关于信任的讨论？",
        "expected_route": "semantic",
        "keywords": ["信任", "讨论"],
        "difficulty": "medium",
    },
    {
        "question": "有什么关于情感表达的建议？",
        "expected_route": "semantic",
        "keywords": ["情感表达", "建议"],
        "difficulty": "medium",
    },
    {
        "question": "视频中讨论了哪些关于代际关系的话题？",
        "expected_route": "semantic",
        "keywords": ["代际关系", "话题"],
        "difficulty": "medium",
    },
    {
        "question": "有哪些关于自我价值的内容？",
        "expected_route": "semantic",
        "keywords": ["自我价值"],
        "difficulty": "medium",
    },
    {
        "question": "视频里提到了哪些关于边界感的讨论？",
        "expected_route": "semantic",
        "keywords": ["边界感", "讨论"],
        "difficulty": "medium",
    },
    {
        "question": "有什么关于情感依赖的分析？",
        "expected_route": "semantic",
        "keywords": ["情感依赖", "分析"],
        "difficulty": "medium",
    },
    {
        "question": "视频中提到了哪些关于治愈的话题？",
        "expected_route": "semantic",
        "keywords": ["治愈", "话题"],
        "difficulty": "medium",
    },
    {
        "question": "有哪些关于情感成熟的观点？",
        "expected_route": "semantic",
        "keywords": ["情感成熟", "观点"],
        "difficulty": "medium",
    },
    {
        "question": "视频里讨论了哪些关于原生家庭的影响？",
        "expected_route": "semantic",
        "keywords": ["原生家庭", "影响"],
        "difficulty": "hard",
    },
    {
        "question": "有什么关于情感修复的建议？",
        "expected_route": "semantic",
        "keywords": ["情感修复", "建议"],
        "difficulty": "hard",
    },
    {
        "question": "视频中提到了哪些关于共情能力的讨论？",
        "expected_route": "semantic",
        "keywords": ["共情能力", "讨论"],
        "difficulty": "hard",
    },
    {
        "question": "有哪些关于情感智慧的深度分析？",
        "expected_route": "semantic",
        "keywords": ["情感智慧", "深度分析"],
        "difficulty": "hard",
    },
]

# ==================== 混合查询（SQL + RAG）- 30 个 ====================

HYBRID_QUERIES = [
    # 统计 + 内容（10 个）
    {
        "question": "桃姐播放量最高的视频讲了什么？",
        "expected_route": "hybrid",
        "keywords": ["桃姐", "播放量", "最高", "内容"],
        "difficulty": "medium",
    },
    {
        "question": "情感类视频的平均播放量是多少？这些视频主要讨论什么话题？",
        "expected_route": "hybrid",
        "keywords": ["情感", "平均播放量", "话题"],
        "difficulty": "hard",
    },
    {
        "question": "最近一周发布的视频中，有哪些关于职场的内容？",
        "expected_route": "hybrid",
        "keywords": ["最近", "一周", "职场"],
        "difficulty": "medium",
    },
    {
        "question": "播放量超过5万的视频中，有哪些关于人际关系的建议？",
        "expected_route": "hybrid",
        "keywords": ["播放量", "5万", "人际关系", "建议"],
        "difficulty": "hard",
    },
    {
        "question": "哪个UP主的视频平均点赞最高？他们的视频主要讲什么？",
        "expected_route": "hybrid",
        "keywords": ["UP主", "平均点赞", "最高", "内容"],
        "difficulty": "hard",
    },
    {
        "question": "最近发布的10个视频中，有哪些关于情感话题的讨论？",
        "expected_route": "hybrid",
        "keywords": ["最近", "发布", "情感", "话题"],
        "difficulty": "medium",
    },
    {
        "question": "弹幕数最多的视频讲了什么内容？",
        "expected_route": "hybrid",
        "keywords": ["弹幕", "最多", "内容"],
        "difficulty": "medium",
    },
    {
        "question": "哪个分类的视频增长最快？这些视频主要讨论什么？",
        "expected_route": "hybrid",
        "keywords": ["分类", "增长", "最快", "话题"],
        "difficulty": "hard",
    },
    {
        "question": "收藏数最高的视频有哪些关于自我成长的建议？",
        "expected_route": "hybrid",
        "keywords": ["收藏", "最高", "自我成长", "建议"],
        "difficulty": "hard",
    },
    {
        "question": "最近一个月播放量增长最快的视频讨论了哪些话题？",
        "expected_route": "hybrid",
        "keywords": ["最近", "一个月", "增长", "最快", "话题"],
        "difficulty": "hard",
    },

    # 复杂分析（10 个）
    {
        "question": "桃姐的视频中，播放量最高的情感话题是什么？",
        "expected_route": "hybrid",
        "keywords": ["桃姐", "播放量", "最高", "情感话题"],
        "difficulty": "hard",
    },
    {
        "question": "哪些UP主的视频既讲婚姻又讲职场？",
        "expected_route": "hybrid",
        "keywords": ["UP主", "婚姻", "职场"],
        "difficulty": "hard",
    },
    {
        "question": "最近发布的视频中，有哪些同时讨论了家庭和情感？",
        "expected_route": "hybrid",
        "keywords": ["最近", "发布", "家庭", "情感"],
        "difficulty": "hard",
    },
    {
        "question": "播放量超过10万的视频中，有哪些关于沟通技巧的内容？",
        "expected_route": "hybrid",
        "keywords": ["播放量", "10万", "沟通技巧"],
        "difficulty": "hard",
    },
    {
        "question": "哪个分类的视频平均弹幕数最高？这些视频主要讨论什么？",
        "expected_route": "hybrid",
        "keywords": ["分类", "平均弹幕", "最高", "话题"],
        "difficulty": "hard",
    },
    {
        "question": "最近一周发布的视频中，有哪些关于心理学的讨论？",
        "expected_route": "hybrid",
        "keywords": ["最近", "一周", "心理学"],
        "difficulty": "hard",
    },
    {
        "question": "点赞数和收藏数都高的视频讲了什么内容？",
        "expected_route": "hybrid",
        "keywords": ["点赞", "收藏", "高", "内容"],
        "difficulty": "hard",
    },
    {
        "question": "哪些UP主的视频既有人际关系又有自我成长的话题？",
        "expected_route": "hybrid",
        "keywords": ["UP主", "人际关系", "自我成长"],
        "difficulty": "hard",
    },
    {
        "question": "播放量最高的前5个视频分别讨论了哪些情感话题？",
        "expected_route": "hybrid",
        "keywords": ["播放量", "前5", "情感话题"],
        "difficulty": "hard",
    },
    {
        "question": "最近发布的视频中，播放量和弹幕数都很高的讲了什么？",
        "expected_route": "hybrid",
        "keywords": ["最近", "发布", "播放量", "弹幕", "高"],
        "difficulty": "hard",
    },

    # 综合分析（10 个）
    {
        "question": "桃姐最近发布的视频中，播放量最高的讲了什么情感话题？",
        "expected_route": "hybrid",
        "keywords": ["桃姐", "最近", "发布", "播放量", "最高", "情感"],
        "difficulty": "hard",
    },
    {
        "question": "哪个UP主的视频平均播放量最高？他们最近讲了什么话题？",
        "expected_route": "hybrid",
        "keywords": ["UP主", "平均播放量", "最高", "最近", "话题"],
        "difficulty": "hard",
    },
    {
        "question": "情感类视频中，播放量超过平均值的有哪些？它们讨论了什么？",
        "expected_route": "hybrid",
        "keywords": ["情感", "播放量", "平均值", "超过", "话题"],
        "difficulty": "hard",
    },
    {
        "question": "最近一个月发布的视频中，弹幕数最多的讲了什么内容？",
        "expected_route": "hybrid",
        "keywords": ["最近", "一个月", "弹幕", "最多", "内容"],
        "difficulty": "hard",
    },
    {
        "question": "哪些视频同时具有高播放量和高弹幕数？它们讨论了什么话题？",
        "expected_route": "hybrid",
        "keywords": ["高播放量", "高弹幕", "话题"],
        "difficulty": "hard",
    },
    {
        "question": "最近一周发布的视频中，哪个UP主的视频播放量最高？讲了什么？",
        "expected_route": "hybrid",
        "keywords": ["最近", "一周", "UP主", "播放量", "最高", "内容"],
        "difficulty": "hard",
    },
    {
        "question": "收藏数最高的前10个视频中，有哪些关于人生感悟的内容？",
        "expected_route": "hybrid",
        "keywords": ["收藏", "最高", "前10", "人生感悟"],
        "difficulty": "hard",
    },
    {
        "question": "哪个分类的视频增长最快？这些视频主要讨论了哪些话题？",
        "expected_route": "hybrid",
        "keywords": ["分类", "增长", "最快", "话题"],
        "difficulty": "hard",
    },
    {
        "question": "播放量超过5万且弹幕数超过100的视频讲了什么？",
        "expected_route": "hybrid",
        "keywords": ["播放量", "5万", "弹幕", "100", "内容"],
        "difficulty": "hard",
    },
    {
        "question": "最近发布的视频中，哪些同时讨论了家庭和职场话题？",
        "expected_route": "hybrid",
        "keywords": ["最近", "发布", "家庭", "职场"],
        "difficulty": "hard",
    },
]

# ==================== 汇总 ====================

ALL_TEST_CASES = STRUCTURED_QUERIES + SEMANTIC_QUERIES + HYBRID_QUERIES

def get_test_cases(route_type=None, difficulty=None):
    """获取测试用例

    Args:
        route_type: 筛选路由类型（structured/semantic/hybrid）
        difficulty: 筛选难度（easy/medium/hard）

    Returns:
        list: 测试用例列表
    """
    cases = ALL_TEST_CASES

    if route_type:
        cases = [c for c in cases if c["expected_route"] == route_type]

    if difficulty:
        cases = [c for c in cases if c["difficulty"] == difficulty]

    return cases

def get_stats():
    """获取测试用例统计"""
    return {
        "total": len(ALL_TEST_CASES),
        "structured": len(STRUCTURED_QUERIES),
        "semantic": len(SEMANTIC_QUERIES),
        "hybrid": len(HYBRID_QUERIES),
        "easy": len([c for c in ALL_TEST_CASES if c["difficulty"] == "easy"]),
        "medium": len([c for c in ALL_TEST_CASES if c["difficulty"] == "medium"]),
        "hard": len([c for c in ALL_TEST_CASES if c["difficulty"] == "hard"]),
    }

if __name__ == "__main__":
    stats = get_stats()
    print(f"测试用例总数: {stats['total']}")
    print(f"  - 结构化查询: {stats['structured']}")
    print(f"  - 语义查询: {stats['semantic']}")
    print(f"  - 混合查询: {stats['hybrid']}")
    print(f"\n难度分布:")
    print(f"  - Easy: {stats['easy']}")
    print(f"  - Medium: {stats['medium']}")
    print(f"  - Hard: {stats['hard']}")
