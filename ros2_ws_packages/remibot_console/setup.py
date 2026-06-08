from pathlib import Path

from setuptools import find_packages, setup

package_name = "remibot_console"
asset_files = [
    (str(Path("share") / package_name / path.parent), [str(path)])
    for path in Path("assets").rglob("*")
    if path.is_file()
]

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(include=["kitchen_qt", "kitchen_qt.*", "remibot_console"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ] + asset_files,
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Peiyu Wang",
    maintainer_email="uyfql@student.kit.edu",
    description="Qt operator console for kitchen arm debugging, simulation, and hardware operation.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "kitchen_arm_gui = kitchen_qt.app:main",
            "visualization_renderer = remibot_console.visualization_renderer:main",
            "rviz_capture_renderer = remibot_console.rviz_capture_renderer:main",
        ],
    },
)
