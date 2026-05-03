"""
社交媒体帖子评估与对比API
用于评估单个帖子或对比两个帖子的表现
"""

import traceback
from flask import request, jsonify

from . import posts_bp
from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..utils.locale import t

logger = get_logger('mirofish.api.posts')


def _build_evaluate_prompt(post_text: str, context: str = "") -> str:
    """构建帖子评估提示词"""
    return f"""你是一个专业的社交媒体营销分析专家。请评估以下社交媒体帖子的表现。

{'背景信息：' + context if context else ''}

待评估帖子：
---
{post_text}
---

请从以下维度进行评估，返回JSON格式结果：

{{
    "score": <总评分 0-100>,
    "engagement_prediction": {{
        "likes": <预估点赞数>,
        "shares": <预估分享数>,
        "comments": <预估评论数>
    }},
    "dimensions": {{
        "clarity": <清晰度 0-100>,
        "emotional_appeal": <情感吸引力 0-100>,
        "shareability": <可分享性 0-100>,
        "relevance": <相关性 0-100>,
        "uniqueness": <独特性 0-100>
    }},
    "strengths": ["<优点1>", "<优点2>", ...],
    "weaknesses": ["<缺点1>", "<缺点2>", ...],
    "improvement_suggestions": ["<建议1>", "<建议2>", ...],
    "target_audience": "<目标受众描述>",
    "best_posting_time": "<建议发布时间>",
    "summary": "<一段话的整体评价>"
}}

评分标准：
- 90-100: 优秀病毒式传播潜力
- 70-89: 良好，有较好互动预期
- 50-69: 中等，需要改进
- 30-49: 较差，效果有限
- 0-29: 很差，不建议发布

请直接返回JSON，不要包含markdown代码块标记。"""


def _build_compare_prompt(post_a_text: str, post_b_text: str, context: str = "") -> str:
    """构建帖子对比提示词"""
    return f"""你是一个专业的社交媒体营销分析专家。请对比以下两个社交媒体帖子的表现。

{'背景信息：' + context if context else ''}

帖子A：
---
{post_a_text}
---

帖子B：
---
{post_b_text}
---

请从以下维度进行对比分析，返回JSON格式结果：

{{
    "winner": "<A或B，表示总体更好的帖子>",
    "scores": {{
        "A": <帖子A总评分 0-100>,
        "B": <帖子B总评分 0-100>
    }},
    "engagement_predictions": {{
        "A": {{"likes": <数>, "shares": <数>, "comments": <数>}},
        "B": {{"likes": <数>, "shares": <数>, "comments": <数>}}
    }},
    "dimension_comparison": {{
        "clarity": {{"winner": "<A或B>", "A_score": <数>, "B_score": <数>, "reason": "<原因>"}},
        "emotional_appeal": {{"winner": "<A或B>", "A_score": <数>, "B_score": <数>, "reason": "<原因>"}},
        "shareability": {{"winner": "<A或B>", "A_score": <数>, "B_score": <数>, "reason": "<原因>"}},
        "relevance": {{"winner": "<A或B>", "A_score": <数>, "B_score": <数>, "reason": "<原因>"}},
        "uniqueness": {{"winner": "<A或B>", "A_score": <数>, "B_score": <数>, "reason": "<原因>"}}
    }},
    "key_differences": ["<差异点1>", "<差异点2>", ...],
    "recommendation": "<针对每个帖子的具体优化建议>",
    "use_case": {{
        "A": "<帖子A最适合的场景>",
        "B": "<帖子B最适合的场景>"
    }},
    "summary": "<两句话总结对比结论>"
}}

请直接返回JSON，不要包含markdown代码块标记。"""


@posts_bp.route('/evaluate', methods=['POST'])
def evaluate_post():
    """
    评估单个社交媒体帖子
    
    Request body (JSON):
        post: str - 要评估的帖子内容
        context: str (optional) - 背景信息，如账号定位、目标受众等
    
    Returns:
        JSON with evaluation scores and suggestions
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400
        
        post = data.get('post', '').strip()
        if not post:
            return jsonify({
                "success": False,
                "error": "帖子内容不能为空"
            }), 400
        
        context = data.get('context', '')
        
        logger.info(f"评估帖子，长度={len(post)}字符")
        
        # 使用LLM评估
        llm = LLMClient()
        prompt = _build_evaluate_prompt(post, context)
        
        messages = [
            {"role": "system", "content": "你是一个专业的社交媒体营销分析专家。始终以JSON格式回复。"},
            {"role": "user", "content": prompt}
        ]
        
        result = llm.chat_json(messages, temperature=0.3)
        
        return jsonify({
            "success": True,
            "data": result,
            "post_length": len(post)
        })
        
    except ValueError as e:
        logger.error(f"LLM返回格式错误: {e}")
        return jsonify({
            "success": False,
            "error": f"评估失败：LLM返回格式错误 - {str(e)}"
        }), 500
    except Exception as e:
        logger.error(f"评估帖子失败: {e}\n{traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": f"评估失败：{str(e)}"
        }), 500


@posts_bp.route('/compare', methods=['POST'])
def compare_posts():
    """
    对比两个社交媒体帖子
    
    Request body (JSON):
        post_a: str - 第一个帖子内容
        post_b: str - 第二个帖子内容
        context: str (optional) - 背景信息
    
    Returns:
        JSON with comparison results
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400
        
        post_a = data.get('post_a', '').strip()
        post_b = data.get('post_b', '').strip()
        
        if not post_a:
            return jsonify({
                "success": False,
                "error": "帖子A内容不能为空"
            }), 400
        
        if not post_b:
            return jsonify({
                "success": False,
                "error": "帖子B内容不能为空"
            }), 400
        
        context = data.get('context', '')
        
        logger.info(f"对比两个帖子，长度A={len(post_a)}，B={len(post_b)}")
        
        # 使用LLM对比
        llm = LLMClient()
        prompt = _build_compare_prompt(post_a, post_b, context)
        
        messages = [
            {"role": "system", "content": "你是一个专业的社交媒体营销分析专家。始终以JSON格式回复。"},
            {"role": "user", "content": prompt}
        ]
        
        result = llm.chat_json(messages, temperature=0.3)
        
        return jsonify({
            "success": True,
            "data": result,
            "post_a_length": len(post_a),
            "post_b_length": len(post_b)
        })
        
    except ValueError as e:
        logger.error(f"LLM返回格式错误: {e}")
        return jsonify({
            "success": False,
            "error": f"对比失败：LLM返回格式错误 - {str(e)}"
        }), 500
    except Exception as e:
        logger.error(f"对比帖子失败: {e}\n{traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": f"对比失败：{str(e)}"
        }), 500
