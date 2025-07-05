from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import sqlite3
from typing import Optional
from contextlib import contextmanager
from pathlib import Path
from rank_calculator import calculate_enhanced_rank, get_detailed_analysis

app = FastAPI(
    title="天津中考位次查询API",
    description="查询2024年天津市六区中考成绩位次",
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
    rank: int
    rank_range: dict  # 添加排名区间
    segment_count: int  # 添加该分数段人数
    total_students: int
    percentage: float
    analysis: str

# 数据库连接管理
@contextmanager
def get_db():
    conn = sqlite3.connect('scores.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

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

@app.get("/api-info")
async def api_info():
    """API信息（原来的根路由）"""
    return {
        "message": "天津中考位次查询API",
        "version": "1.0.0",
        "endpoints": {
            "/": "查询界面",
            "/rank": "查询位次API",
            "/stats": "统计信息API",
            "/docs": "API文档",
            "/redoc": "API文档(ReDoc)"
        }
    }

@app.post("/rank", response_model=RankResponse)
async def query_rank(query: ScoreQuery):
    """
    查询2024年天津市六区中考成绩位次
    
    - **score**: 中考分数（0-800分，支持0.1分精度）
    """
    try:
        # 验证分数精度（支持0.01分）
        if round(query.score * 100) != query.score * 100:
            raise HTTPException(
                status_code=400,
                detail="分数仅支持保留两位小数（如750.25、750.50）"
            )
        
        # 使用增强版的计算函数
        rank_result = calculate_enhanced_rank(query.score, year=2024, db_path='scores.db')
        
        if rank_result['total_students'] == 0:
            raise HTTPException(
                status_code=500,
                detail="无法获取数据，请稍后重试"
            )
        
        # 生成详细分析
        analysis = get_detailed_analysis(rank_result)
        
        return RankResponse(
            score=query.score,
            rank=rank_result['rank'],
            rank_range=rank_result['rank_range'],
            segment_count=rank_result['segment_count'],
            total_students=rank_result['total_students'],
            percentage=rank_result['percentage'],
            analysis=analysis
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"查询失败：{str(e)}"
        )

@app.get("/stats")
async def get_statistics():
    """获取2024年市六区统计信息"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 获取最高分、最低分、总人数
            cursor.execute("""
                SELECT 
                    MAX(CASE WHEN inner_six > 0 THEN score ELSE NULL END) as max_score,
                    MIN(CASE WHEN inner_six > 0 THEN score ELSE NULL END) as min_score,
                    SUM(inner_six) as total_students
                FROM score_records
                WHERE year = 2024
            """)
            result = cursor.fetchone()
            
            # 获取各分数段人数
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN score >= 750 THEN '750分以上'
                        WHEN score >= 700 THEN '700-749分'
                        WHEN score >= 650 THEN '650-699分'
                        WHEN score >= 600 THEN '600-649分'
                        WHEN score >= 550 THEN '550-599分'
                        ELSE '550分以下'
                    END as score_range,
                    SUM(inner_six) as count
                FROM score_records
                WHERE year = 2024
                GROUP BY score_range
                ORDER BY MIN(score) DESC
            """)
            
            score_distribution = [
                {"range": row[0], "count": row[1]} 
                for row in cursor.fetchall()
            ]
            
            return {
                "year": 2024,
                "region": "天津市六区",
                "max_score": result['max_score'],
                "min_score": result['min_score'],
                "total_students": result['total_students'],
                "score_distribution": score_distribution
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败：{str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)