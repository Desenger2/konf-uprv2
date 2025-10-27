import json
import sys
import urllib.request
import urllib.error

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
        dependencies = get_package_dependencies(
            config.package_name, 
            config.version, 
            config.repository_url
        )
        
        print("Прямые зависимости:")
        for dep in dependencies:
            print(f"- {dep}")
            
    except Exception as e:
        print(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    main()