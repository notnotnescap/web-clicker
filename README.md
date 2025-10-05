# Web Clicker

This is a simple python web server designed to run on a laptop running a presentation. It serves a single web page that has next and previous buttons that send keyboard events to the laptop.

This project was created to solve the signal range limitations of standard presentation remotes. By serving a simple web page, it allows any device on the same network, such as your phone, to act as a remote. This approach also allows for easy customization of the remote's layout and functionality.

## Requirements
- Python 3.7 or higher
- [uv](https://github.com/astral-sh/uv)

## Usage

```sh
uv run main.py
```

Or double click `run.bat` on Windows.

Then open a web browser and navigate to `http://<your-laptop-ip>:8000/<secret>`, where `<your-laptop-ip>` is the IP address of the laptop running the server, and `<secret>` is the secret defined in `main.py` (default is `web-clicker`).
