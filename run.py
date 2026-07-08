"""妙喵私教 启动入口"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("ewa.api.main:app", host="0.0.0.0", port=8000, reload=True)
