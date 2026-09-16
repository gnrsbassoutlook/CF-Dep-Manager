import gradio as gr
import subprocess
import os
import glob


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


def find_package_in_plugins(pkg_name: str, content_map: dict):
    if isinstance(pkg_name, list):
        pkg_name = pkg_name[0] if pkg_name else ""
    if not pkg_name.strip() or not content_map:
        return []

    pkg_lower = pkg_name.strip().lower()
    choices = []

    for file_path, content in content_map.items():
        ver_info = ""
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name_part = line
            for sep in ["==", ">=", "<=", "~=", "!="]:
                if sep in line:
                    name_part = line.split(sep)[0]
                    break
            if name_part.strip().lower() == pkg_lower:
                ver_info = line.strip()
                break
        if ver_info:
            choices.append((f"{file_path}    {ver_info}", file_path))

    return choices


# ---------------------- 界面 ----------------------
with gr.Blocks(title="ComfyUI 依赖管理器") as demo:
    gr.Markdown("## ComfyUI 便携版依赖管理器")

    with gr.Row():
        python_path = gr.Textbox(label="Python 目录", value=r"E:\ComfyUI\python", scale=3)
        custom_nodes_path = gr.Textbox(label="插件目录", value=r"E:\ComfyUI\ComfyUI\custom_nodes", scale=3)
        refresh_btn = gr.Button("刷新全部", scale=1, variant="primary")

    with gr.Row():
        # 左列：系统依赖 + 插件文件详情
        with gr.Column(scale=2):
            pip_output = gr.Textbox(label="系统依赖列表 (pip list)", lines=16, interactive=False)
            export_btn = gr.Button("导出为 TXT")
            export_file = gr.File(visible=False)

            gr.Markdown("### 插件 requirements 文件详情")
            with gr.Row():
                req_file_select = gr.Dropdown(
                    label="选择文件查看完整内容",
                    choices=[],
                    filterable=True,
                    allow_custom_value=True,
                    scale=3
                )
                scan_req_btn = gr.Button("重新扫描插件目录", scale=1)
            req_content = gr.Textbox(label="文件内容", lines=12, interactive=False)

        # 右列：搜索操作 + 反向查询
        with gr.Column(scale=1):
            gr.Markdown("### 依赖搜索与操作")
            pkg_select = gr.Dropdown(
                label="选择/搜索依赖包（输入字母自动匹配）",
                choices=[],
                filterable=True,
                allow_custom_value=True
            )
            pkg_version = gr.Textbox(label="当前已安装版本", interactive=False)

            with gr.Row():
                no_deps_check = gr.Checkbox(label="不安装依赖 (--no-deps)", value=False, scale=2)
                install_btn = gr.Button("安装", variant="primary", scale=1)
                uninstall_btn = gr.Button("卸载", variant="stop", scale=1)

            exec_log = gr.Textbox(label="执行日志", lines=5, interactive=False)

            gr.Markdown("### 插件反向查询")
            plugin_file_select = gr.Dropdown(
                label="包含该依赖的插件（点击查看完整内容）",
                choices=[],
                filterable=True,
                allow_custom_value=True
            )

    # 状态存储
    pkg_dict_state = gr.State({})
    file_content_state = gr.State({})

    # ---------------------- 事件 ----------------------

    def refresh_all(py_dir, custom_dir):
        # 获取系统依赖
        try:
            pip_text, pkg_dict, pkg_list = get_pip_list(py_dir)
        except Exception as e:
            pip_text = f"[error] 获取系统依赖失败：{e}"
            pkg_dict = {}
            pkg_list = []

        # 扫描插件
        try:
            req_files, content_map = scan_custom_requirements(custom_dir)
        except Exception as e:
            req_files = []
            content_map = {"[error]": f"扫描插件目录失败：{e}"}

        # 标准写法：用 gr.update 更新下拉框选项
        return (
            pip_text,
            pkg_dict,
            gr.update(choices=pkg_list),   # 更新依赖包下拉选项
            gr.update(choices=req_files),  # 更新插件文件下拉选项
            content_map
        )

    refresh_btn.click(
        fn=refresh_all,
        inputs=[python_path, custom_nodes_path],
        outputs=[
            pip_output,
            pkg_dict_state,
            pkg_select,
            req_file_select,
            file_content_state
        ]
    )

    # 选中依赖包 → 显示版本 + 更新反向查询下拉选项
    def on_pkg_select(selected_pkg, pkg_dict, content_map):
        if isinstance(selected_pkg, list):
            selected_pkg = selected_pkg[0] if selected_pkg else ""
        if not selected_pkg:
            return "", gr.update(choices=[])
        
        ver = pkg_dict.get(selected_pkg.lower(), "未安装")
        plugin_choices = find_package_in_plugins(selected_pkg, content_map)
        return ver, gr.update(choices=plugin_choices)

    pkg_select.change(
        fn=on_pkg_select,
        inputs=[pkg_select, pkg_dict_state, file_content_state],
        outputs=[pkg_version, plugin_file_select]
    )

    # 反向查询选中文件 → 直接显示内容
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

    # 左侧文件选择 → 显示内容
    def show_file_content(selected_file, content_map):
        if isinstance(selected_file, list):
            selected_file = selected_file[0] if selected_file else ""
        if not selected_file:
            return ""
        return content_map.get(selected_file, "")

    req_file_select.change(
        fn=show_file_content,
        inputs=[req_file_select, file_content_state],
        outputs=[req_content]
    )

    # 安装
    install_btn.click(
        fn=install_package,
        inputs=[python_path, pkg_select, no_deps_check],
        outputs=[exec_log]
    )

    # 卸载
    uninstall_btn.click(
        fn=uninstall_package,
        inputs=[python_path, pkg_select],
        outputs=[exec_log]
    )

    # 导出
    def export_txt(pip_text):
        if not pip_text or not pip_text.strip():
            return gr.update(visible=False)
        save_path = "pip_list_export.txt"
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(pip_text)
        return gr.update(value=save_path, visible=True)

    export_btn.click(fn=export_txt, inputs=[pip_output], outputs=[export_file])

    # 重新扫描插件
    def rescan_plugins(custom_dir):
        try:
            req_files, content_map = scan_custom_requirements(custom_dir)
        except Exception as e:
            req_files = []
            content_map = {"[error]": f"扫描失败：{e}"}
        return gr.update(choices=req_files), content_map

    scan_req_btn.click(
        fn=rescan_plugins,
        inputs=[custom_nodes_path],
        outputs=[req_file_select, file_content_state]
    )


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=8186,
        inbrowser=True
    )
