import configparser
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel
import yaml
import toml

from .utils import ensure_list, package_path

class ConfigItem(BaseModel):
    value: dict = {}
    preload: bool = False
    prefix: str = ""
    envvars: Dict[str, str] = {}

    def __init__(self, **data):
        super().__init__(**data)
        if self.preload:
            self.value = self.__process_config(self.value)

    def __getattr__(self, name: str):
        """通过属性方式访问配置项

        Args:
            name (str): 配置项名称

        Returns:
            Any: 如果配置项是字典则返回ConfigItem对象,否则返回原始值。
            如果配置项不存在返回None。
        """
        if name in self.value:
            item = self.value[name]
            if isinstance(item, dict):
                return ConfigItem(value=item, preload=self.preload, prefix=self.prefix, envvars=self.envvars)
            else:
                if self.preload:
                    # 值已经处理过,直接返回
                    return item
                else:
                    return self.__process_value(item)
        else:
            return None

    def __setattr__(self, name: str, value):
        """通过属性方式设置配置项

        Args:
            name (str): 配置项名称
            value: 配置项的值
        """
        if name == "value":
            super().__setattr__(name, value)
        else:
            print(f"ConfigItem.__setattr__(): {name}: {value}")
            self.value[name] = value

    def to_dict(self) -> dict:
        """将配置转换为字典

        Returns:
            dict: 配置数据字典
        """
        return self.value

    def __process_value(self, value: Any) -> str:
        if isinstance(value, str):
            if value.startswith("@file "):
                # @file path
                file = value[6:]
                if file.startswith("$"):
                    file = self.__get_env_var(file[1:])
                return Path(file).read_text(encoding="utf-8")
            elif value.startswith("$"):
                # environment variable
                return self.__get_env_var(value[1:])
            elif value.lower() in ["true", "false"]:
                # boolean
                return value.lower() == "true"

        return value

    def __get_env_var(self, key: str) -> str:
        if self.prefix and not key.startswith(self.prefix):
            prefixed_key = f"{self.prefix}_{key}"
            if prefixed_key in os.environ:
                return self.envvars[prefixed_key] or os.getenv(prefixed_key)
        return self.envvars[key] or os.getenv(key)
    
    def __process_config(self, cfg: dict) -> dict:
        c = {}
        for k, v in cfg.items():
            if isinstance(v, dict):
                c[k] = self.__process_config(v)
            else:
                c[k] = self.__process_value(v)
        return c


class Config(BaseModel):
    """配置管理类,用于加载和管理应用配置。

    该类支持从多个配置文件(yaml/json/toml/ini)和环境变量加载配置。
    配置项可以通过属性方式访问。

    Args:
        config_files (List[str]): 配置文件名列表,默认为["config.yaml"]
        config_dir (List[str]): 配置文件目录列表,默认为["config"]
        prefix (str): 环境变量前缀,默认为"APP"
        config (Dict): 配置数据字典

    Examples:
        >>> cfg = Config(
        ...     config_files=["config.yaml", "local.yaml"],
        ...     config_dir=["config", "conf"],
        ...     prefix="MYAPP"
        ... )
        >>> print(cfg.database.host)
        localhost
        >>> print(cfg.api.port)
        8080
    """

    config_files: List[str] = ["config.yaml"]
    config_dir: List[str] = ["config"]
    config: ConfigItem = ConfigItem()
    prefix: str = "APP"
    preload: bool = False
    dotenv: bool = False
    envvars: Dict[str, str] = {}

    def __init__(self, **data: Any):
        super().__init__(**data)
        super().__setattr__("config_files", ensure_list(self.config_files, str))
        super().__setattr__("config_dir", ensure_list(self.config_dir, str))
        self.load()

    def load(self) -> dict:
        """加载所有配置

        从配置文件和环境变量加载配置,并合并所有配置。
        环境变量的配置会覆盖配置文件中的同名配置。

        Returns:
            dict: 合并后的配置字典
        """
        logger.debug(
            f"Config(): files: {self.config_files}, dir: {self.config_dir}, prefix: {self.prefix}, dotenv: {self.dotenv}"
        )
        if self.dotenv:
            load_dotenv()
        cfg_from_env = self.load_env()
        cfg_from_file = self.load_files()
        cfg_final = deep_update(cfg_from_file, cfg_from_env)
        cfg = ConfigItem(value=cfg_final, preload=self.preload, prefix=self.prefix, envvars=self.envvars)
        super().__setattr__("config", cfg)
        logger.debug(f"load(): {cfg}")
        return self.to_dict()

    def load_env(self) -> dict:
        """从环境变量加载配置

        加载以prefix为前缀的环境变量作为配置项。
        环境变量名会被转换为小写作为配置项名。

        Returns:
            dict: 从环境变量加载的配置字典
        """
        cfg = {}
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                key = self.__get_env_key_name(key)
                cfg[key] = value
                logger.debug(f"load_env(): {key}: {value}")
        return cfg

    def load_files(self) -> dict:
        """从配置文件加载配置

        按照config_files和config_dir的设置,
        从当前目录到根目录搜索并加载所有配置文件。
        支持yaml/json/toml/ini格式的配置文件。

        Returns:
            dict: 从配置文件加载并合并后的配置字典
        """
        # all config files
        files = self.__get_config_files(Path.cwd())
        # logger.debug(f"load_files(): files: {files}")
        # load all configs
        cfgs = []
        for f in files:
            cfg = self.__load_config_file(f)
            logger.debug(f"load_files(): {f}: {cfg}")
            cfgs.append(cfg)
        # merge all configs
        cfg = {}
        for c in cfgs:
            cfg = deep_update(cfg, c)
        logger.debug(f"load_files(): merged config: {cfg}")
        return cfg

    def to_dict(self) -> dict:
        """将配置转换为字典

        Returns:
            dict: 配置数据字典
        """
        return self.config.to_dict()

    def __getattr__(self, name: str):
        """通过属性方式访问配置项

        Args:
            name (str): 配置项名称

        Returns:
            Any: 如果配置项是字典则返回ConfigItem对象,否则返回原始值。
            如果配置项不存在返回None。
        """
        return self.config.__getattr__(name)

    def __setattr__(self, name: str, value):
        """通过属性方式设置配置项

        Args:
            name (str): 配置项名称
            value: 配置项的值
        """
        self.config.__setattr__(name, value)

    # private
    def __get_env_key_name(self, key: str) -> str:
        """获取环境变量对应的配置项名

        移除环境变量前缀并转换为小写。

        Args:
            key (str): 环境变量名

        Returns:
            str: 配置项名
        """
        # remove prefix
        key = str(key)
        key = key[len(self.prefix) + 1 :]
        # to lower case
        return key.lower()

    def __get_config_files(self, base_dir: Path) -> list[Path]:
        """获取所有配置文件路径

        从base_dir开始向上搜索所有可能的配置文件路径。

        Args:
            base_dir (Path): 起始搜索目录

        Returns:
            list[Path]: 存在的配置文件路径列表
        """
        # get all possible config dirs from base_dir to root
        dirs = []
        # from given path to root
        while base_dir != Path("/"):
            dirs.append(base_dir)
            # if config_dir is set, also add them to current path
            if self.config_dir:
                for d in self.config_dir:
                    dirs.append(base_dir.joinpath(d))
            base_dir = base_dir.parent
        # from package path to root
        base_dir = Path(package_path())
        while base_dir != Path("/"):
            if base_dir in dirs:
                # if the path is already in the list, so the parent path is also in the list
                break
            dirs.append(base_dir)
            # if config_dir is set, also add them to current path
            if self.config_dir:
                for d in self.config_dir:
                    dirs.append(base_dir.joinpath(d))
            base_dir = base_dir.parent
        # attach config files to each path
        files = []
        for p in dirs:
            for f in self.config_files:
                files.append(p.joinpath(f))
        # varify if the path exists
        files_existed = [f for f in files if f.exists()]
        return files_existed

    def __load_config_file(self, path: Path) -> dict:
        """加载单个配置文件

        根据文件扩展名选择相应的加载方法。

        Args:
            path (Path): 配置文件路径

        Returns:
            dict: 配置数据字典
        """
        cfg = {}
        if path.suffix == ".json":
            cfg = self.__load_config_file_json(path)
        elif path.suffix == ".toml":
            cfg = self.__load_config_file_toml(path)
        elif path.suffix == ".ini":
            cfg = self.__load_config_file_ini(path)
        elif path.suffix == ".yaml":
            cfg = self.__load_config_file_yaml(path)
        else:
            logger.warning(f"Unknown file type: {path.suffix}")
        # process config
        if self.preload:
            cfg = self.__preload(cfg)
        return cfg

    def __load_config_file_yaml(self, path: Path) -> dict:
        """加载YAML配置文件

        Args:
            path (Path): 配置文件路径

        Returns:
            dict: 配置数据字典
        """
        cfg = yaml.safe_load(path.read_text())
        return cfg

    def __load_config_file_json(self, path: Path) -> dict:
        """加载JSON配置文件

        Args:
            path (Path): 配置文件路径

        Returns:
            dict: 配置数据字典
        """
        cfg = json.loads(path.read_text())
        return cfg

    def __load_config_file_toml(self, path: Path) -> dict:
        """加载TOML配置文件

        Args:
            path (Path): 配置文件路径

        Returns:
            dict: 配置数据字典
        """
        cfg = toml.loads(path.read_text())
        return cfg

    def __load_config_file_ini(self, path: Path) -> dict:
        """加载INI配置文件

        Args:
            path (Path): 配置文件路径

        Returns:
            dict: 配置数据字典
        """
        cfg = configparser.ConfigParser()
        cfg.read(path)
        return cfg


def deep_update(old: dict, newer: dict) -> dict:
    """深度更新字典

    递归地将newer字典的内容更新到old字典中。
    对于嵌套的字典会进行递归更新。

    Args:
        old (dict): 被更新的字典
        newer (dict): 用于更新的字典

    Returns:
        dict: 更新后的字典

    Examples:
        >>> old = {"a": 1, "b": {"c": 2}}
        >>> newer = {"b": {"d": 3}}
        >>> result = deep_update(old, newer)
        >>> print(result)
        {'a': 1, 'b': {'c': 2, 'd': 3}}
    """
    c = old.copy()
    for k, v in newer.items():
        if isinstance(v, dict):
            c[k] = deep_update(c.get(k, {}), v)
        else:
            c[k] = v
    return c

