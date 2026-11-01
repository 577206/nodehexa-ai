from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'firmware/lingji-xjwb03'))


def serve():
    from aiohttp import web
    from omni_bridge import Controller, create_app
    config = {'LINGXI_BOARD_URL': 'http://192.168.31.186:8766',
              'LINGXI_BRIDGE_TOKEN': 'a' * 64, 'DASHSCOPE_API_KEY': 'qa-only'}
    web.run_app(create_app(Controller(config)), host='127.0.0.1', port=8765)


def check():
    from qa_studio_v2 import main
    main()


if __name__ == '__main__':
    if '--serve' in sys.argv:
        serve()
    else:
        check()
