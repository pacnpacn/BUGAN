from setuptools import setup, find_packages

setup(
    name="bugan",
    url="https://github.com/buganart/BUGAN",
    author="buganart",
    description="3D GANs and more.",
    packages=find_packages(),
    install_requires=[
        "ConfigArgParse",
        "disjoint-set==0.6.3",
        "Pillow",
        "pytorch_lightning",
        "numpy",
        "torch",
        "torchsummary",
        "tqdm",
        "trimesh",
        "scipy",
        "scikit-image",
        "wandb",
    ],
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
)
