import os
import sys
import subprocess

def main():
    # 현재 스크립트(kordoc.py)가 위치한 디렉토리 (bin 폴더)
    bin_dir = os.path.dirname(os.path.abspath(__file__))
    is_windows = os.name == 'nt'
    
    # OS 환경에 맞는 내장 Node.js 실행파일 경로 선택
    if is_windows:
        node_exe = os.path.join(bin_dir, 'windows_x86_64', 'bin', 'node.exe')
    else:
        node_exe = os.path.join(bin_dir, 'linux_x86_64', 'bin', 'node')
        
    js_script = os.path.join(bin_dir, 'kordoc_app.js')
    
    # Python으로 들어온 인수(예: file="문서.hwpx")를 Node.js로 전달
    cmd = [node_exe, js_script] + sys.argv[1:]
    
    # Splunk 엔진과 표준 입출력(stdin/stdout)을 유지하여 데이터 반환
    process = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr, stdin=sys.stdin)
    process.communicate()
    sys.exit(process.returncode)

if __name__ == '__main__':
    main()
