import gradio as gr
import subprocess
import os
import glob
import json
import re
import configparser
import argparse

# ---------------------- 路径与配置管理 ----------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CURRENT_DIR, "cdm_config.json")
DEFAULT_PORT = 8186


def load_saved_port() -> int:
    """读取保存的端口配置，若无则使用默认端口 8186"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("port", DEFAULT_PORT))
        except:
            pass
    return DEFAULT_PORT


def save_and_sync_port(new_port) -> str:
    """保存端口到 json，并同步修改同目录下的 launch_cdm.bat"""
    try:
        new_port = int(new_port)
        if not (1024 <= new_port <= 65535):
            return "❌ 端口范围应在 1024 ~ 65535 之间！"
    except (ValueError, TypeError):
        return "❌ 请输入有效的数字端口号！"

    # 1. 保存到 cdm_config.json
    try:
        cfg = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        cfg["port"] = new_port
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        return f"❌ 写入配置文件失败: {str(e)}"

    # 2. 同步修改同目录下的 bat 脚本 (launch_cdm.bat 或 launch.bat)
    bat_synced = False
    bat_candidates = ["launch_cdm.bat", "launch.bat"]
    for bat_name in bat_candidates:
        bat_path = os.path.join(CURRENT_DIR, bat_name)
        if os.path.isfile(bat_path):
            try:
                with open(bat_path, "r", encoding="utf-8", errors="replace") as f:
                    bat_content = f.read()

                # 替换 set "PORT=xxxx" 或 http://127.0.0.1:xxxx
                bat_content = re.sub(r'set\s+"PORT=\d+"', f'set "PORT={new_port}"', bat_content)
                bat_content = re.sub(r'127\.0\.0\.1:\d+', f'127.0.0.1:{new_port}', bat_content)

                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write(bat_content)
                bat_synced = True
            except Exception as e:
                return f"⚠️ 端口已记录，但同步修改 {bat_name} 失败: {str(e)}"

    bat_msg = "✅ `launch_cdm.bat` 已同步修改！" if bat_synced else "ℹ️ 未在同级目录找到 bat 文件（已仅保存配置）。"
    return (
        f"🎉 **端口已成功修改为 `{new_port}`！**\n\n"
        f"{bat_msg}\n\n"
        f"⚠️ **请关闭当前命令终端黑窗口，重新双击运行 `launch_cdm.bat` 重启生效！**"
    )


# ---------------------- 核心业务函数 ----------------------
def get_python_exe(python_dir: str) -> str:
    return os.path.join(python_dir.strip(), "python.exe")


def get_pip_list(python_dir: str):
    python_exe = get_python_exe(python_dir)
    if not os.path.exists(python_exe):
        return f"错误：找不到 Python 可执行文件\n{python_exe}", {}, []

    try:
        result = subprocess.run(
            [python_exe, "-m", "pip", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        raw = result.stdout + result.stderr

        pkg_dict = {}
        pkg_list = []
        data_rows = []

        for line in raw.splitlines():
            line = line.strip()
            if not line or "---" in line or line.lower().startswith("package"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                name, ver = parts[0], parts[1]
                pkg_dict[name.lower()] = ver
                pkg_list.append(name)
                data_rows.append((name, ver))

        if data_rows:
            max_name_len = max(len(n) for n, _ in data_rows)
            header = f"{'Package'.ljust(max_name_len)}    {'Version'.rjust(15)}"
            separator = f"{'-' * max_name_len}    {'-' * 15}"
            body = [f"{n.ljust(max_name_len)}    {v.rjust(15)}" for n, v in data_rows]
            formatted = "\n".join([header, separator] + body)
        else:
            formatted = raw

        return formatted, pkg_dict, sorted(pkg_list)
    except Exception as e:
        return f"执行出错：{str(e)}", {}, []


def install_package(python_dir: str, package_name: str, no_deps: bool) -> str:
    python_exe = get_python_exe(python_dir)
    if not os.path.exists(python_exe):
        return f"错误：找不到 Python 可执行文件\n{python_exe}"

    if isinstance(package_name, list):
        package_name = package_name[0] if package_name else ""
    package_name = package_name.strip()
    if not package_name:
        return "请先选择或输入要安装的依赖包名"

    cmd = [python_exe, "-m", "pip", "install", package_name]
    if no_deps:
        cmd.append("--no-deps")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace"
        )
        return result.stdout + "\n" + result.stderr
    except Exception as e:
        return f"安装出错：{str(e)}"


def uninstall_package(python_dir: str, package_name: str) -> str:
    python_exe = get_python_exe(python_dir)
    if not os.path.exists(python_exe):
        return f"错误：找不到 Python 可执行文件\n{python_exe}"

    if isinstance(package_name, list):
        package_name = package_name[0] if package_name else ""
    package_name = package_name.strip()
    if not package_name:
        return "请先选择或输入要卸载的依赖包名"

    cmd = [python_exe, "-m", "pip", "uninstall", package_name, "-y"]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace"
        )
        return result.stdout + "\n" + result.stderr
    except Exception as e:
        return f"卸载出错：{str(e)}"


def scan_custom_requirements(custom_nodes_dir: str):
    if not os.path.isdir(custom_nodes_dir):
        return [], {"错误": f"插件目录不存在：{custom_nodes_dir}"}

    pattern = os.path.join(custom_nodes_dir, "**", "requirements*.txt")
    req_files = sorted(set(glob.glob(pattern, recursive=True)))

    if not req_files:
        return [], {"提示": "未找到任何 requirements 相关文件"}

    file_list = []
    content_map = {}
    for fp in req_files:
        rel = os.path.relpath(fp, custom_nodes_dir)
        file_list.append(rel)
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                content_map[rel] = f.read()
        except Exception as e:
            content_map[rel] = f"读取失败：{str(e)}"

    return file_list, content_map


def get_plugin_git_url(custom_nodes_dir: str, file_rel_path: str) -> str:
    plugin_dir_name = os.path.dirname(file_rel_path)
    if not plugin_dir_name:
        return ""
    plugin_full_path = os.path.join(custom_nodes_dir, plugin_dir_name)
    return extract_repo_url(plugin_full_path)


def read_git_url_from_config(plugin_dir: str) -> str:
    git_config = os.path.join(plugin_dir, ".git", "config")
    if not os.path.isfile(git_config):
        return ""
    try:
        config = configparser.ConfigParser()
        config.read(git_config, encoding="utf-8")
        if 'remote "origin"' in config:
            url = config['remote "origin"'].get("url", "")
            if url:
                if url.startswith("git@"):
                    url = url.replace("git@github.com:", "https://github.com/")
                if url.endswith(".git"):
                    url = url[:-4]
                return url.rstrip("/")
    except:
        pass
    return ""


def extract_repo_url(plugin_dir: str) -> str:
    if not os.path.isdir(plugin_dir):
        return ""

    manifest_path = os.path.join(plugin_dir, "manifest.json")
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            repo = data.get("repository", "")
            if isinstance(repo, dict):
                repo = repo.get("url", "")
            elif isinstance(repo, list) and repo:
                repo = repo[0]
            if isinstance(repo, str) and repo.startswith("http"):
                return repo.rstrip("/")
        except:
            pass

    init_path = os.path.join(plugin_dir, "__init__.py")
    if os.path.isfile(init_path):
        try:
            with open(init_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            patterns = [
                r'GITHUB_REPO\s*=\s*[\'"](.+?)[\'"]',
                r'REPO_URL\s*=\s*[\'"](.+?)[\'"]',
                r'__github__\s*=\s*[\'"](.+?)[\'"]',
                r'github\.com/[^\s"\'<>]+'
            ]
            for pat in patterns:
                match = re.search(pat, content, re.IGNORECASE)
                if match:
                    url = match.group(0) if pat.startswith(r'github') else match.group(1)
                    if not url.startswith("http"):
                        url = "https://" + url
                    return url.rstrip("/")
        except:
            pass

    url = read_git_url_from_config(plugin_dir)
    if url:
        return url

    git_dir = os.path.join(plugin_dir, ".git")
    if os.path.isdir(git_dir):
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=plugin_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            url = result.stdout.strip()
            if url.startswith("git@"):
                url = url.replace("git@github.com:", "https://github.com/")
            if url.endswith(".git"):
                url = url[:-4]
            if url:
                return url.rstrip("/")
        except:
            pass

    return ""


def scan_all_plugin_git(custom_nodes_dir: str):
    if not os.path.isdir(custom_nodes_dir):
        return 0, 0, []

    total = 0
    git_plugins = []

    for item in sorted(os.listdir(custom_nodes_dir)):
        item_path = os.path.join(custom_nodes_dir, item)
        if not os.path.isdir(item_path):
            continue
        total += 1
        
        url = extract_repo_url(item_path)
        if url:
            git_plugins.append((item, url))

    return total, len(git_plugins), git_plugins


def build_git_links_md(plugin_list):
    if not plugin_list:
        return "*未找到匹配的插件*"
    lines = []
    for name, url in plugin_list:
        lines.append(f'- <span style="font-size: 1.15em;">[{name}]({url}){{target=_blank}}</span>')
    return "\n".join(lines)


def parse_version(ver_str: str):
    try:
        ver_str = ver_str.strip()
        m = re.match(r'(\d+(?:\.\d+)*)', ver_str)
        if not m:
            return (0,)
        return tuple(int(p) for p in m.group(1).split('.'))
    except:
        return (0,)


def check_version_constraint(current_ver: str, constraint: str) -> bool:
    if not constraint or not current_ver or current_ver == "未安装":
        return True
    
    current = parse_version(current_ver)
    constraint = constraint.strip()
    
    match = re.match(r'(==|>=|<=|>|<|~=|!=)\s*(.+)', constraint)
    if not match:
        op = '>='
        ver = constraint
    else:
        op, ver = match.groups()
    
    target = parse_version(ver)
    
    if op == '==':
        return current == target
    elif op == '>=':
        return current >= target
    elif op == '<=':
        return current <= target
    elif op == '>':
        return current > target
    elif op == '<':
        return current < target
    elif op == '!=':
        return current != target
    elif op == '~=':
        return current >= target and current[0] == target[0]
    else:
        return True


def find_package_in_plugins(pkg_name: str, content_map: dict, current_version: str = ""):
    if isinstance(pkg_name, list):
        pkg_name = pkg_name[0] if pkg_name else ""
    if not pkg_name.strip() or not content_map:
        return []

    pkg_lower = pkg_name.strip().lower()
    choices = []

    for file_path, content in content_map.items():
        ver_info = ""
        constraint_str = ""
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name_part = line
            for sep in ["==", ">=", "<=", "~=", "!="]:
                if sep in line:
                    idx = line.find(sep)
                    name_part = line[:idx]
                    constraint_str = line[idx:]
                    break
            else:
                name_part = line
                constraint_str = ""
            
            if name_part.strip().lower() == pkg_lower:
                ver_info = line.strip()
                break
        if ver_info:
            display_text = f"{file_path}    {ver_info}"
            if current_version and current_version != "未安装":
                if not check_version_constraint(current_version, constraint_str):
                    display_text = f"⚠️ 冲突  {display_text}"
            choices.append((display_text, file_path))

    return choices


# ---------------------- 界面构建 ----------------------
CURRENT_PORT = load_saved_port()

with gr.Blocks(title="CF-Dep-Manager") as demo:
    gr.Markdown("## CF-Dep-Manager 依赖管理器")

    # 顶部配置栏与折叠端口管理
    with gr.Row():
        python_path = gr.Textbox(label="Python 目录", value=r"E:\ComfyUI\python", scale=4)
        custom_nodes_path = gr.Textbox(label="插件目录", value=r"E:\ComfyUI\ComfyUI\custom_nodes", scale=4)
        refresh_btn = gr.Button("刷新全部", scale=1, variant="primary")

    with gr.Accordion("⚙️ 服务与端口设置", open=False):
        with gr.Row():
            port_input = gr.Number(
                label="服务端口号 (Port)",
                value=CURRENT_PORT,
                precision=0,
                scale=2
            )
            save_port_btn = gr.Button("保存新端口并同步更新 bat", variant="secondary", scale=2)
        port_sync_result = gr.Markdown("")

    with gr.Row():
        # 左列
        with gr.Column(scale=2):
            pip_output = gr.Textbox(label="系统依赖列表 (pip list)", lines=14, interactive=False)
            with gr.Row():
                export_btn = gr.Button("导出为 TXT")
            export_file = gr.File(visible=False)

            gr.Markdown("#### 插件 requirements 文件详情")
            with gr.Row():
                req_file_select = gr.Dropdown(
                    label="选择文件",
                    choices=[],
                    filterable=True,
                    allow_custom_value=True,
                    scale=3
                )
                scan_req_btn = gr.Button("重新扫描", scale=1)
            
            plugin_git_link = gr.Markdown("")
            req_content = gr.Textbox(label="文件内容", lines=10, interactive=False)

            gr.Markdown("#### 插件 GitHub 仓库一览")
            git_stats = gr.Markdown("")
            plugin_search = gr.Textbox(label="搜索插件名称", placeholder="输入关键词过滤，如：layerstyle")
            all_git_links = gr.Markdown("", height=400)

        # 右列
        with gr.Column(scale=1):
            gr.Markdown("#### 依赖搜索与操作")
            pkg_select = gr.Dropdown(
                label="选择/搜索依赖包",
                choices=[],
                filterable=True,
                allow_custom_value=True
            )
            pkg_version = gr.Textbox(label="当前已安装版本", interactive=False)

            with gr.Row():
                no_deps_check = gr.Checkbox(label="不安装依赖 (--no-deps)", value=False, scale=2)
                install_btn = gr.Button("安装", variant="primary", scale=1)
                uninstall_btn = gr.Button("卸载", variant="stop", scale=1)

            exec_log = gr.Textbox(label="执行日志", lines=4, interactive=False)

            gr.Markdown("#### 插件反向查询")
            plugin_file_select = gr.Dropdown(
                label="包含该依赖的插件",
                choices=[],
                filterable=True,
                allow_custom_value=True
            )

    # 状态存储
    pkg_dict_state = gr.State({})
    file_content_state = gr.State({})
    all_git_plugins_state = gr.State([])

    # ---------------------- 事件绑定 ----------------------

    # 保存端口事件
    save_port_btn.click(
        fn=save_and_sync_port,
        inputs=[port_input],
        outputs=[port_sync_result]
    )

    def refresh_all(py_dir, custom_dir):
        try:
            pip_text, pkg_dict, pkg_list = get_pip_list(py_dir)
        except Exception as e:
            pip_text = f"[error] 获取系统依赖失败：{e}"
            pkg_dict = {}
            pkg_list = []

        try:
            req_files, content_map = scan_custom_requirements(custom_dir)
        except Exception as e:
            req_files = []
            content_map = {"[error]": f"扫描插件目录失败：{e}"}

        total, git_count, git_plugins = scan_all_plugin_git(custom_dir)
        stats_text = f"共 **{total}** 个插件，已关联 GitHub：**{git_count}** 个，未识别：**{total - git_count}** 个"
        links_md = build_git_links_md(git_plugins)

        return (
            pip_text,
            pkg_dict,
            gr.update(choices=pkg_list),
            gr.update(choices=req_files),
            content_map,
            "",
            stats_text,
            git_plugins,
            links_md
        )

    refresh_btn.click(
        fn=refresh_all,
        inputs=[python_path, custom_nodes_path],
        outputs=[
            pip_output,
            pkg_dict_state,
            pkg_select,
            req_file_select,
            file_content_state,
            req_content,
            git_stats,
            all_git_plugins_state,
            all_git_links
        ]
    )

    def filter_git_plugins(keyword, plugin_list):
        if not keyword.strip():
            return build_git_links_md(plugin_list)
        kw = keyword.strip().lower()
        filtered = [(n, u) for n, u in plugin_list if kw in n.lower()]
        return build_git_links_md(filtered)

    plugin_search.input(
        fn=filter_git_plugins,
        inputs=[plugin_search, all_git_plugins_state],
        outputs=[all_git_links]
    )

    def on_pkg_select(selected_pkg, pkg_dict, content_map):
        if isinstance(selected_pkg, list):
            selected_pkg = selected_pkg[0] if selected_pkg else ""
        if not selected_pkg:
            return "", gr.update(choices=[])
        
        ver = pkg_dict.get(selected_pkg.lower(), "未安装")
        plugin_choices = find_package_in_plugins(selected_pkg, content_map, ver)
        return ver, gr.update(choices=plugin_choices)

    pkg_select.change(
        fn=on_pkg_select,
        inputs=[pkg_select, pkg_dict_state, file_content_state],
        outputs=[pkg_version, plugin_file_select]
    )

    def on_plugin_file_select(selected_file, content_map):
        if isinstance(selected_file, list):
            selected_file = selected_file[0] if selected_file else ""
        if not selected_file:
            return ""
        return content_map.get(selected_file, "")

    plugin_file_select.change(
        fn=on_plugin_file_select,
        inputs=[plugin_file_select, file_content_state],
        outputs=[req_content]
    )

    def show_file_content(selected_file, custom_dir, content_map):
        if isinstance(selected_file, list):
            selected_file = selected_file[0] if selected_file else ""
        if not selected_file:
            return "", ""
        
        content = content_map.get(selected_file, "")
        git_url = get_plugin_git_url(custom_dir, selected_file)
        if git_url:
            link_md = f"**🔗 插件 GitHub 主页：[{git_url}]({git_url}){{target=_blank}}**"
        else:
            link_md = "*未检测到 Git 仓库地址*"
        return content, link_md

    req_file_select.change(
        fn=show_file_content,
        inputs=[req_file_select, custom_nodes_path, file_content_state],
        outputs=[req_content, plugin_git_link]
    )

    install_btn.click(
        fn=install_package,
        inputs=[python_path, pkg_select, no_deps_check],
        outputs=[exec_log]
    )

    uninstall_btn.click(
        fn=uninstall_package,
        inputs=[python_path, pkg_select],
        outputs=[exec_log]
    )

    def export_txt(pip_text):
        if not pip_text or not pip_text.strip():
            return gr.update(visible=False)
        save_path = "pip_list_export.txt"
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(pip_text)
        return gr.update(value=save_path, visible=True)

    export_btn.click(fn=export_txt, inputs=[pip_output], outputs=[export_file])

    def rescan_plugins(custom_dir):
        try:
            req_files, content_map = scan_custom_requirements(custom_dir)
            total, git_count, git_plugins = scan_all_plugin_git(custom_dir)
            stats_text = f"共 **{total}** 个插件，已关联 GitHub：**{git_count}** 个，未识别：**{total - git_count}** 个"
            links_md = build_git_links_md(git_plugins)
        except Exception as e:
            req_files = []
            content_map = {"[error]": f"扫描失败：{e}"}
            stats_text = "扫描失败"
            git_plugins = []
            links_md = ""
        return gr.update(choices=req_files), content_map, stats_text, git_plugins, links_md

    scan_req_btn.click(
        fn=rescan_plugins,
        inputs=[custom_nodes_path],
        outputs=[req_file_select, file_content_state, git_stats, all_git_plugins_state, all_git_links]
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CF-Dep-Manager")
    parser.add_argument("--port", type=int, default=CURRENT_PORT, help="Server port")
    args = parser.parse_args()

    actual_port = args.port
    print(f"[*] CF-Dep-Manager 正在启动，端口: {actual_port}")

    demo.launch(
        server_name="127.0.0.1",
        server_port=actual_port,
        inbrowser=True
    )