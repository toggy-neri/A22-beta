import subprocess
import sys
import os
import time
import atexit

processes = []

def cleanup():
    print('\n正在停止所有服务...')
    for p in processes:
        try:
            print(f'停止进程 PID={p.pid}...')
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        except Exception as e:
            print(f'停止进程时出错: {e}')
    print('所有服务已停止')

def get_python_path():
    venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'Scripts', 'python.exe')
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable

def run_livetalking():
    livetalking_path = os.path.join(os.path.dirname(__file__), 'LiveTalking')
    python_path = get_python_path()
    
    cmd = [
        python_path, 'app.py',
        '--transport', 'webrtc',
        '--model', 'wav2lip',
        '--avatar_id', '贴心女医生',
        '--tts', 'qwentts',
        '--REF_FILE', 'Cherry',
        '--qwen_tts_model', 'qwen3-tts-flash-realtime'
    ]
    
    print(f'[LiveTalking] 启动命令: {" ".join(cmd)}')
    print(f'[LiveTalking] 工作目录: {livetalking_path}')
    print(f'[LiveTalking] Python: {python_path}')
    
    p = subprocess.Popen(cmd, cwd=livetalking_path)
    processes.append(p)
    return p

def run_backend():
    backend_path = os.path.dirname(__file__)
    python_path = get_python_path()
    
    cmd = [python_path, 'main.py']
    
    print(f'[Backend] 启动命令: {" ".join(cmd)}')
    print(f'[Backend] 工作目录: {backend_path}')
    print(f'[Backend] Python: {python_path}')
    
    p = subprocess.Popen(cmd, cwd=backend_path)
    processes.append(p)
    return p

def main():
    atexit.register(cleanup)
    
    print('=' * 60)
    print('启动数字人服务...')
    print('=' * 60)
    
    python_path = get_python_path()
    print(f'\n使用 Python: {python_path}')
    
    print('\n[1/2] 启动 LiveTalking 服务 (端口 8010)...')
    livetalking_proc = run_livetalking()
    
    print('\n等待 LiveTalking 初始化...')
    time.sleep(5)
    
    print('\n[2/2] 启动后端服务 (端口 12345)...')
    backend_proc = run_backend()
    
    print('\n' + '=' * 60)
    print('所有服务已启动!')
    print('  - LiveTalking: http://localhost:8010')
    print('  - 后端API:    http://localhost:12345')
    print('  - 前端页面:   打开 frontend/dist/index.html')
    print('=' * 60)
    print('\n按 Ctrl+C 停止所有服务...\n')
    
    try:
        while True:
            livetalking_poll = livetalking_proc.poll()
            backend_poll = backend_proc.poll()
            
            if livetalking_poll is not None:
                print(f'[LiveTalking] 进程已退出，退出码: {livetalking_poll}')
                break
            if backend_poll is not None:
                print(f'[Backend] 进程已退出，退出码: {backend_poll}')
                break
            
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n收到中断信号...')
    finally:
        cleanup()

if __name__ == '__main__':
    main()
