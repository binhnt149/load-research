[app]
title = LoadResearch
project_dir = ..
input_file = launcher.py
exec_directory = ../dist/native
project_file =
icon =

[python]
packages = Nuitka==4.1.1

[qt]
qml_files =
excluded_qml_plugins =
modules = Core,Gui,Widgets
plugins = platforms

[nuitka]
macos.permissions =
mode = standalone
extra_args = --clang --jobs=2 --windows-console-mode=attach --assume-yes-for-downloads --enable-plugin=dill-compat --noinclude-qt-translations --include-package=load_research --include-package=tzdata --include-package=scipy._external.array_api_compat.numpy --include-package=sklearn.externals.array_api_compat.numpy --include-module=matplotlib.backends.backend_svg --include-package-data=tzdata --include-package-data=matplotlib --include-package-data=sklearn
