#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "fastapi>=0.118.0",
#     "pynput>=1.8.1",
#     "python-multipart>=0.0.20",
#     "uvicorn>=0.37.0",
#     "websockets>=15.0.1",
#     "pywin32>=311; sys_platform == 'win32'",
# ]
# ///

import platform
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from pynput.keyboard import Controller, Key

if platform.system() == "Windows":
    import win32com.client
    import win32gui

app = FastAPI()
keyboard = Controller()
SECRET = "9WvE75cjPwYLtw"  # This password is of little importance, just prevents random people from accessing the page if they find the IP


def list_windows():
    """Lists all visible windows with a title."""
    if platform.system() != "Windows":
        print("Window listing is only supported on Windows.")
        return

    def winEnumHandler(hwnd, ctx):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) != "":
            print(f"  - '{win32gui.GetWindowText(hwnd)}'")

    print("Available windows:")
    win32gui.EnumWindows(winEnumHandler, None)
    print("-" * 20)


def focus_slide_window():
    """Switch to the window ending with PowerPoint Presenter View"""
    if platform.system() != "Windows":
        print("Window focusing is only supported on Windows.")
        return

    try:

        def winEnumHandler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd).endswith(
                "PowerPoint Presenter View"
            ):
                shell = win32com.client.Dispatch("WScript.Shell")
                shell.SendKeys("%")  # Send Alt key to prevent focus stealing issues
                win32gui.SetForegroundWindow(hwnd)
                return

        win32gui.EnumWindows(winEnumHandler, None)
    except Exception as e:
        print(f"Error focusing window: {e}")


# HTML content for the frontend with embedded JavaScript
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Web Clicker</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            body { 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                height: 80vh;
                margin: 0; 
                background-color: #282c34; 
                font-family: sans-serif;
                text-align: center;
            }
            .arrows {
                display: flex;
                justify-content: center;
                align-items: center;
                width: 100%;
            }
            .arrow { 
                display: flex;
                flex-direction: column;
                align-items: center;
                flex-grow: 1;
                cursor: pointer; 
                user-select: none; 
                color: #61dafb; 
                margin: 0 20px;
                padding: 10px 0;
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
            .legend {
                font-size: 1.2em;
                margin-top: 5px;
                color: white;
            }
            #status {
                position: fixed;
                top: 10px;
                left: 50%;
                transform: translateX(-50%);
                padding: 8px 12px;
                border-radius: 5px;
                color: white;
                font-size: 1.2em;
                font-weight: bold;
            }
            .connected { background-color: #28a745; }
            .disconnected { background-color: #dc3545; }
            .reconnecting { background-color: #ffc107; color: #212529;}
            * {
                touch-action: manipulation;
            }
            .fullscreen-btn {
                position: fixed;
                bottom: 20px;
                right: 20px;
                cursor: pointer;
                color: #61dafb;
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 50%;
                width: 50px;
                height: 50px;
                display: flex;
                justify-content: center;
                align-items: center;
            }

            /* Stack arrows vertically on narrow screens */
            @media (max-width: 350px) {
                .arrows {
                    flex-direction: column;
                    gap: 16px;
                }
                .arrow {
                    margin: 0;
                    width: 100%;
                }
            }
        </style>
    </head>
    <body>
        <div id="status">Connecting...</div>
        <div class="arrows">
            <div id="left" class="arrow">
                <svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-left-icon lucide-arrow-left"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
                <div class="legend">Previous</div>
            </div>
            <div id="right" class="arrow">
                <svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-right-icon lucide-arrow-right"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                <div class="legend">Next</div>
            </div>
        </div>
        <div id="fullscreenBtn" class="fullscreen-btn">
            <svg id="enter-fullscreen" xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="m21 3-7 7"/><path d="m3 21 7-7"/></svg>
            <svg id="exit-fullscreen" xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:none;"><path d="M9 3H3v6"/><path d="M15 21h6v-6"/><path d="m3 3 7 7"/><path d="m21 21-7-7"/></svg>
        </div>
        <script>
            const leftArrow = document.getElementById('left');
            const rightArrow = document.getElementById('right');
            const statusDiv = document.getElementById('status');
            const fullscreenBtn = document.getElementById('fullscreenBtn');
            const enterFullscreenIcon = document.getElementById('enter-fullscreen');
            const exitFullscreenIcon = document.getElementById('exit-fullscreen');
            let ws;
            const path = window.location.pathname;
            const secret = path.substring(path.lastIndexOf('/') + 1);

            function updateStatus(message, className) {
                statusDiv.textContent = message;
                statusDiv.className = '';
                statusDiv.classList.add(className);
            }

            function connect() {
                ws = new WebSocket(`ws://${window.location.host}/ws`);
                updateStatus('Connecting...', 'reconnecting');

                ws.onopen = function(event) {
                    console.log("Connected to WebSocket.");
                    updateStatus('Connected', 'connected');
                };

                ws.onclose = function(event) {
                    console.log("WebSocket disconnected. Attempting to reconnect...");
                    updateStatus('Disconnected', 'disconnected');
                    setTimeout(connect, 2000);
                };

                ws.onerror = function(error) {
                    console.error("WebSocket error:", error);
                };
            }

            function sendMessage(action) {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    const payload = {
                        secret: secret,
                        action: action
                    };
                    ws.send(JSON.stringify(payload));
                } else {
                    console.log("Cannot send message, WebSocket is not open.");
                }
            }

            function toggleFullScreen() {
                if (!document.fullscreenElement && !document.mozFullScreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement) {
                    if (document.documentElement.requestFullscreen) {
                        document.documentElement.requestFullscreen();
                    } else if (document.documentElement.msRequestFullscreen) {
                        document.documentElement.msRequestFullscreen();
                    } else if (document.documentElement.mozRequestFullScreen) {
                        document.documentElement.mozRequestFullScreen();
                    } else if (document.documentElement.webkitRequestFullscreen) {
                        document.documentElement.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
                    }
                } else {
                    if (document.exitFullscreen) {
                        document.exitFullscreen();
                    } else if (document.msExitFullscreen) {
                        document.msExitFullscreen();
                    } else if (document.mozCancelFullScreen) {
                        document.documentElement.mozCancelFullScreen();
                    } else if (document.webkitExitFullscreen) {
                        document.webkitExitFullscreen();
                    }
                }
            }

            function updateFullscreenIcons() {
                const isFullscreen = document.fullscreenElement || document.mozFullScreenElement || document.webkitFullscreenElement || document.msFullscreenElement;
                if (isFullscreen) {
                    enterFullscreenIcon.style.display = 'none';
                    exitFullscreenIcon.style.display = 'block';
                } else {
                    enterFullscreenIcon.style.display = 'block';
                    exitFullscreenIcon.style.display = 'none';
                }
            }

            fullscreenBtn.onclick = toggleFullScreen;

            document.addEventListener('fullscreenchange', updateFullscreenIcons);
            document.addEventListener('webkitfullscreenchange', updateFullscreenIcons);
            document.addEventListener('mozfullscreenchange', updateFullscreenIcons);
            document.addEventListener('MSFullscreenChange', updateFullscreenIcons);

            leftArrow.onclick = () => {
                sendMessage('left');
                if (navigator.vibrate) {
                    navigator.vibrate(10);
                }
                leftArrow.style.backgroundColor = 'rgba(97, 218, 251, 0.3)';
                setTimeout(() => {
                    leftArrow.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                }, 100);
            };
            rightArrow.onclick = () => {
                sendMessage('right');
                if (navigator.vibrate) {
                    navigator.vibrate(10);
                }
                rightArrow.style.backgroundColor = 'rgba(97, 218, 251, 0.3)';
                setTimeout(() => {
                    rightArrow.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                }, 100);
            };

            connect();
        </script>
    </body>
</html>
"""


@app.get("/{secret_path:path}")
async def get(secret_path: str):
    # if secret_path != SECRET:
    #     raise HTTPException(status_code=404, detail="Not Found")
    if secret_path == SECRET:
        return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                if data.get("secret") != SECRET:
                    print("Invalid secret received. Ignoring.")
                    continue

                action = data.get("action")
                if action == "left":
                    # focus_slide_window()
                    # time.sleep(0.1)  # slight delay to ensure window focus
                    keyboard.press(Key.left)
                    keyboard.release(Key.left)
                    print(f"{websocket.client.host} : Left arrow pressed")
                elif action == "right":
                    # focus_slide_window()
                    # time.sleep(0.1)  # slight delay to ensure window focus
                    keyboard.press(Key.right)
                    keyboard.release(Key.right)
                    print(f"{websocket.client.host} : Right arrow pressed")
                elif action == "mute":
                    # keyboard.press(Key.f13)
                    # keyboard.release(Key.f13)
                    keyboard.press(".")
                    keyboard.release(".")
                    print(f"{websocket.client.host} : Mute toggled")
            except (json.JSONDecodeError, AttributeError):
                print("Invalid data format received. Ignoring.")
                continue

    except WebSocketDisconnect:
        print("Client disconnected")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
