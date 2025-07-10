import sys
import os
import random
from pathlib import Path

# 确保当前目录在Python路径中
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional
import time
from rank_calculator import calculate_enhanced_rank, get_detailed_analysis
from data import get_year_stats, get_score_distribution
from school_recommender import recommend_schools_by_rank
from api_auth import verify_api_key_with_delay, blur_rank_data, blur_score_data, should_blur_data, API_KEY_INFO
from request_logger import request_logger

app = FastAPI(
    title="天津中考位次查询API",
    description="查询2025年天津市六区中考成绩位次",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
STATIC_PATH = Path(__file__).parent.parent / "frontend" / "static"
if STATIC_PATH.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")

# 数据模型
class ScoreQuery(BaseModel):
    score: float = Field(..., ge=0, le=800, description="中考分数（0-800）")

class RankResponse(BaseModel):
    score: float
    rank: int  # 全市排名
    inner_rank: int  # 市六区排名
    rank_range: dict  # 添加排名区间
    segment_count: int  # 添加该分数段人数
    total_students: int  # 全市总学生数
    total_students_inner: int  # 市六区总学生数
    percentage: float  # 全市百分位
    inner_percentage: float  # 市六区百分位
    analysis: str

# 数据库连接管理已被移除，现在直接使用静态数据

# 这些函数已经从 rank_calculator 模块导入，不再需要在这里定义

# 获取前端文件路径
FRONTEND_PATH = Path(__file__).parent.parent / "frontend"

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def welcome():
    """显示欢迎页面，直接重定向到查询界面"""
    # 直接返回查询界面
    html_file = FRONTEND_PATH / "index.html"
    if html_file.exists():
        with open(html_file, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>欢迎使用天津中考位次查询API</h1><p>请访问 <a href='/app'>查询界面</a> 或 <a href='/docs'>API文档</a></p>")

@app.get("/app", response_class=HTMLResponse, 
         summary="查询界面",
         description="天津中考位次查询Web界面",
         tags=["前端页面"])
async def serve_app():
    """提供查询界面（会在API文档中显示）"""
    html_file = FRONTEND_PATH / "index.html"
    if html_file.exists():
        # 读取HTML文件并修改API地址
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 不修改API地址，保持原样
        
        return HTMLResponse(content=html_content)
    else:
        raise HTTPException(status_code=404, detail="前端文件未找到")

@app.get("/recommend-app", response_class=HTMLResponse,
         summary="志愿推荐界面",
         description="天津中考志愿推荐（冲稳保）Web界面",
         tags=["前端页面"])
async def serve_recommend_app():
    """提供志愿推荐界面"""
    html_file = FRONTEND_PATH / "recommend.html"
    if html_file.exists():
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    else:
        raise HTTPException(status_code=404, detail="推荐页面文件未找到")

@app.get("/admin/stats", 
         summary="统计页面",
         description="查看API请求统计和日志",
         tags=["管理页面"])
async def serve_stats_page():
    """提供统计页面"""
    html_file = FRONTEND_PATH / "stats.html"
    if html_file.exists():
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    else:
        raise HTTPException(status_code=404, detail="统计页面文件未找到")

@app.get("/api/stats",
         summary="获取统计数据",
         description="获取API请求统计和日志数据",
         tags=["API"])
async def get_request_stats():
    """获取请求统计数据"""
    try:
        stats = request_logger.get_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        print(f"获取统计数据失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取统计数据失败：{str(e)}"
        )

@app.get("/api-info")
async def api_info():
    """API信息（原来的根路由）"""
    return {
        "message": "天津中考位次查询API",
        "version": "1.0.0",
        "endpoints": {
            "/": "查询界面",
            "/rank": "查询位次API",
            "/recommend": "志愿推荐API",
            "/stats": "统计信息API",
            "/docs": "API文档",
            "/redoc": "API文档(ReDoc)"
        },
        "api_key_required": True,
        "api_key_info": API_KEY_INFO
    }

@app.post("/rank", response_model=RankResponse)
async def query_rank(
    request: Request,
    query: ScoreQuery,
    api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    查询2025年天津市六区中考成绩位次
    
    - **score**: 中考分数（0-800分，支持0.1分精度）
    - **X-API-Key**: API密钥（通过请求头传递）
    """
    start_time = time.time()
    print(f"🔍 [DEBUG] 收到查询请求: score={query.score}")
    
    # 获取客户端信息
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # 验证API密钥
    status_code = 200
    error_msg = None
    
    try:
        is_valid = await verify_api_key_with_delay(api_key)
    except HTTPException as e:
        status_code = e.status_code
        error_msg = e.detail
        # 记录请求日志
        request_logger.log_request(
            endpoint="/rank",
            api_key=api_key,
            is_valid_key=False,
            status_code=status_code,
            response_time=time.time() - start_time,
            client_ip=client_ip,
            user_agent=user_agent,
            request_data={"score": query.score},
            error=error_msg
        )
        raise
    except Exception as e:
        print(f"❌ [AUTH] 密钥验证异常: {str(e)}")
        is_valid = False
    print(f"🔍 [DEBUG] 当前工作目录: {os.getcwd()}")
    print(f"🔍 [DEBUG] 目录内容: {os.listdir('.')}")
    
    # 检查数据库文件存在性
    db_paths_to_check = ['scores.db', '/app/backend/scores.db', './scores.db']
    for db_path in db_paths_to_check:
        exists = os.path.exists(db_path)
        print(f"🔍 [DEBUG] 数据库路径 {db_path}: {'存在' if exists else '不存在'}")
        if exists:
            print(f"🔍 [DEBUG] 文件大小: {os.path.getsize(db_path)} bytes")
    
    try:
        # 验证分数精度（支持0.01分，修复浮点数精度问题）
        score_str = str(query.score)
        decimal_index = score_str.find('.')
        if decimal_index != -1 and len(score_str) - decimal_index - 1 > 2:
            raise HTTPException(
                status_code=400,
                detail="分数仅支持保留两位小数（如750.25、750.50）"
            )
        
        print(f"🔍 [DEBUG] 开始调用 calculate_enhanced_rank...")
        
        # 使用增强版的计算函数
        rank_result = calculate_enhanced_rank(query.score, year=2025)
        
        print(f"🔍 [DEBUG] 计算结果: {rank_result}")
        
        if rank_result['total_students'] == 0:
            raise HTTPException(
                status_code=500,
                detail="无法获取数据，请稍后重试"
            )
        
        # 生成详细分析
        analysis = get_detailed_analysis(rank_result)
        
        print(f"🔍 [DEBUG] 分析完成，准备返回结果")
        
        # 无论是否有有效密钥，都返回真实数据
        # （延迟和错误已经在 verify_api_key_with_delay 中处理）
        # 记录请求日志
        request_logger.log_request(
            endpoint="/rank",
            api_key=api_key,
            is_valid_key=is_valid,
            status_code=status_code,
            response_time=time.time() - start_time,
            client_ip=client_ip,
            user_agent=user_agent,
            request_data={"score": query.score}
        )
        
        return RankResponse(
            score=query.score,
            rank=rank_result['rank'],
            inner_rank=rank_result['inner_rank'],
            rank_range=rank_result['rank_range'],
            segment_count=rank_result['segment_count'],
            total_students=rank_result['total_students'],
            total_students_inner=rank_result['total_students_inner'],
            percentage=rank_result['percentage'],
            inner_percentage=rank_result['inner_percentage'],
            analysis=analysis
        )
        
    except Exception as e:
        print(f"❌ [DEBUG] 查询失败: {str(e)}")
        print(f"❌ [DEBUG] 错误类型: {type(e).__name__}")
        import traceback
        print(f"❌ [DEBUG] 错误堆栈: {traceback.format_exc()}")
        
        # 记录错误请求
        request_logger.log_request(
            endpoint="/rank",
            api_key=api_key,
            is_valid_key=is_valid if 'is_valid' in locals() else False,
            status_code=500,
            response_time=time.time() - start_time,
            client_ip=client_ip,
            user_agent=user_agent,
            request_data={"score": query.score},
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"查询失败：{str(e)}"
        )

@app.get("/stats")
async def get_statistics():
    """获取2025年市六区统计信息"""
    print(f"🔍 [DEBUG] /stats 请求开始")
    
    try:
        print(f"🔍 [DEBUG] 从静态数据获取统计信息...")
        
        # 获取基础统计信息
        stats = get_year_stats(2025)
        if not stats:
            raise HTTPException(status_code=404, detail="未找到2025年数据")
        
        print(f"🔍 [DEBUG] 基础统计查询完成: {stats}")
        
        # 获取分数段分布
        score_distribution = get_score_distribution(2025)
        print(f"🔍 [DEBUG] 分数分布查询完成: {score_distribution}")
        
        response_data = {
            "year": 2025,
            "region": "天津市六区",
            "max_score": stats['max_score'],
            "min_score": stats['min_score'],
            "total_students": stats['total_students'],
            "score_distribution": score_distribution
        }
        print(f"🔍 [DEBUG] /stats 响应数据准备完成")
        return response_data
        
    except Exception as e:
        print(f"❌ [DEBUG] /stats 错误: {str(e)}")
        print(f"❌ [DEBUG] 错误类型: {type(e).__name__}")
        import traceback
        print(f"❌ [DEBUG] 错误堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败：{str(e)}"
        )

class RecommendationQuery(BaseModel):
    rank: int = Field(..., ge=1, le=40000, description="市六区位次")
    
class RecommendationResponse(BaseModel):
    rank: int
    recommendations: dict
    total_schools: int

@app.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(
    request: Request,
    query: RecommendationQuery,
    api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    根据市六区位次推荐志愿学校（冲稳保）
    
    - **rank**: 市六区位次（1-40000）
    - **X-API-Key**: API密钥（通过请求头传递）
    """
    start_time = time.time()
    print(f"🔍 [DEBUG] 收到推荐请求: rank={query.rank}")
    
    # 获取客户端信息
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # 验证API密钥
    status_code = 200
    error_msg = None
    
    try:
        is_valid = await verify_api_key_with_delay(api_key)
    except HTTPException as e:
        status_code = e.status_code
        error_msg = e.detail
        # 记录请求日志
        request_logger.log_request(
            endpoint="/recommend",
            api_key=api_key,
            is_valid_key=False,
            status_code=status_code,
            response_time=time.time() - start_time,
            client_ip=client_ip,
            user_agent=user_agent,
            request_data={"rank": query.rank},
            error=error_msg
        )
        raise
    except Exception as e:
        print(f"❌ [AUTH] 密钥验证异常: {str(e)}")
        is_valid = False
    
    try:
        # 获取推荐结果
        recommendations = recommend_schools_by_rank(query.rank)
        
        # 计算总推荐学校数
        total_schools = sum(len(schools) for schools in recommendations.values())
        
        print(f"🔍 [DEBUG] 推荐完成: 冲{len(recommendations['冲'])}所，稳{len(recommendations['稳'])}所，保{len(recommendations['保'])}所")
        
        # 无论是否有有效密钥，都返回真实数据
        # （延迟和错误已经在 verify_api_key_with_delay 中处理）
        
        # 记录请求日志
        request_logger.log_request(
            endpoint="/recommend",
            api_key=api_key,
            is_valid_key=is_valid,
            status_code=status_code,
            response_time=time.time() - start_time,
            client_ip=client_ip,
            user_agent=user_agent,
            request_data={"rank": query.rank}
        )
        
        return RecommendationResponse(
            rank=query.rank,
            recommendations=recommendations,
            total_schools=total_schools
        )
        
    except Exception as e:
        print(f"❌ [DEBUG] 推荐失败: {str(e)}")
        import traceback
        print(f"❌ [DEBUG] 错误堆栈: {traceback.format_exc()}")
        
        # 记录错误请求
        request_logger.log_request(
            endpoint="/recommend",
            api_key=api_key,
            is_valid_key=is_valid if 'is_valid' in locals() else False,
            status_code=500,
            response_time=time.time() - start_time,
            client_ip=client_ip,
            user_agent=user_agent,
            request_data={"rank": query.rank},
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"推荐失败：{str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)