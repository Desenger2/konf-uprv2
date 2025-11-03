import json
import sys
import urllib.request
import urllib.error
import re

class Config:
    def __init__(self):
        self.package_name = ""
        self.repository_url = ""
        self.test_mode = False
        self.version = ""
        self.max_depth = 0
        self.filter_substring = ""
    
    def load_from_file(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise Exception("Файл конфигурации не найден")
        except json.JSONDecodeError:
            raise Exception("Ошибка формата JSON в файле конфигурации")
        except Exception as e:
            raise Exception(f"Ошибка чтения файла: {str(e)}")
        
        try:
            self.package_name = data.get("package_name", "")
            if not isinstance(self.package_name, str):
                raise ValueError("package_name должен быть строкой")
            
            self.repository_url = data.get("repository_url", "")
            if not isinstance(self.repository_url, str):
                raise ValueError("repository_url должен быть строкой")
            
            self.test_mode = data.get("test_mode", False)
            if not isinstance(self.test_mode, bool):
                raise ValueError("test_mode должен быть логическим значением")
            
            self.version = data.get("version", "")
            if not isinstance(self.version, str):
                raise ValueError("version должен быть строкой")
            
            self.max_depth = data.get("max_depth", 0)
            if not isinstance(self.max_depth, int) or self.max_depth < 0:
                raise ValueError("max_depth должен быть неотрицательным целым числом")
            
            self.filter_substring = data.get("filter_substring", "")
            if not isinstance(self.filter_substring, str):
                raise ValueError("filter_substring должен быть строкой")
                
        except ValueError as e:
            raise Exception(f"{str(e)}")
        except Exception as e:
            raise Exception(f"{str(e)}")

def get_package_info(package_name, repository_url):
    """Получает информацию о пакете, включая последнюю версию"""
    try:
        url = f"{repository_url}/{package_name}/json"
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError:
        raise Exception("Ошибка подключения к репозиторию")
    except Exception as e:
        raise Exception(f"Ошибка получения информации о пакете: {str(e)}")

def get_package_dependencies(package_name, version, repository_url):
    try:
        url = f"{repository_url}/{package_name}/{version}/json"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
        
        dependencies = []
        if 'info' in data and 'requires_dist' in data['info']:
            dependencies = data['info']['requires_dist'] or []
        
        return dependencies
    except urllib.error.URLError:
        raise Exception("Ошибка подключения к репозиторию")
    except Exception as e:
        raise Exception(f"Ошибка получения зависимостей: {str(e)}")

def get_test_dependencies(package_name, version, test_repo_path):
    try:
        with open(test_repo_path, 'r') as f:
            repo_data = json.load(f)
        
        package_key = f"{package_name}=={version}"
        return repo_data.get(package_key, [])
    except Exception as e:
        raise Exception(f"Ошибка чтения тестового репозитория: {str(e)}")

def extract_package_info(dep_string):
    """Извлекает имя пакета и версию из строки зависимости"""
    dep_string = re.split(r'[;<>]', dep_string)[0].strip()
    
    match = re.match(r'^([a-zA-Z0-9._-]+)', dep_string)
    if not match:
        return None, None
    
    package_name = match.group(1)
    
    version_match = re.search(r'==\s*([a-zA-Z0-9._-]+)', dep_string)
    package_version = version_match.group(1) if version_match else None
    
    return package_name, package_version

def get_latest_package_version(package_name, repository_url):
    """Получает последнюю версию пакета из репозитория"""
    try:
        info = get_package_info(package_name, repository_url)
        return info['info']['version']
    except Exception:
        return None

def build_dependency_graph(config, current_package, current_version, current_depth=0, visited=None, path=None):
    if visited is None:
        visited = set()
    if path is None:
        path = []
    
    if current_depth > config.max_depth:
        return {}
    
    package_key = f"{current_package}=={current_version}"
    
    if config.filter_substring and config.filter_substring in current_package:
        return {}
    
    # Проверка на циклическую зависимость
    if package_key in path:
        cycle_path = " -> ".join(path + [package_key])
        print(f"Обнаружена циклическая зависимость: {cycle_path}")
        return {}
    
    # Проверка на уже посещенный пакет (чтобы избежать повторной обработки)
    if package_key in visited:
        return {package_key: {}}
    
    visited.add(package_key)
    path.append(package_key)
    
    try:
        if config.test_mode:
            dependencies = get_test_dependencies(current_package, current_version, config.repository_url)
        else:
            dependencies = get_package_dependencies(current_package, current_version, config.repository_url)
    except Exception as e:
        print(f"Ошибка при получении зависимостей для {package_key}: {str(e)}")
        dependencies = []
    
    graph = {}
    for dep in dependencies:
        dep_name, dep_version = extract_package_info(dep)
        
        if not dep_name:
            continue
            
        if config.filter_substring and config.filter_substring in dep_name:
            continue

        if not dep_version and not config.test_mode:
            dep_version = get_latest_package_version(dep_name, config.repository_url)
            if not dep_version:
                print(f"Не удалось определить версию для пакета {dep_name}")
                continue
        
        if config.test_mode and not dep_version:
            dep_version = config.version
        
        if not dep_version:
            continue
            
        sub_deps = build_dependency_graph(config, dep_name, dep_version, current_depth + 1, visited, path.copy())
        dep_key = f"{dep_name}=={dep_version}"
        graph[dep_key] = sub_deps
    
    path.pop()
    return graph

def print_graph(graph, indent=0):
    for package, dependencies in graph.items():
        print("  " * indent + f"- {package}")
        print_graph(dependencies, indent + 1)

def main():
    if len(sys.argv) != 2:
        print("Для конфигурации введите: python Main.py <файл_конфигурации>")
        sys.exit(1)
    
    config = Config()
    try:
        config.load_from_file(sys.argv[1])
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        sys.exit(1)
    
    try:
        if config.test_mode:
            print("Режим тестирования:")
        else:
            print("Режим реального репозитория:")
        
        graph = build_dependency_graph(config, config.package_name, config.version)
        
        print("\nГраф зависимостей:")
        print_graph(graph)
            
    except Exception as e:
        print(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    main()