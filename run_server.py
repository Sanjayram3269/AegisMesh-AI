import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import uvicorn

if __name__ == '__main__':
    from app.main import app
    uvicorn.run(app, host='0.0.0.0', port=8000)
