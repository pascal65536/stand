import requests
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any
import time
from dataclasses import dataclass
from urllib.parse import urlparse
import json
import behoof


load_dotenv()

@dataclass
class GitHubRepoInfo:
    """Класс для хранения информации о репозитории"""
    owner: str
    repo: str
    url: str
    description: str
    stars: int
    forks: int
    created_at: str
    updated_at: str

@dataclass
class CommitInfo:
    """Класс для хранения информации о коммите"""
    sha: str
    author: str
    message: str
    date: str
    url: str

class GitHubAnalyzer:
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
        self.rate_limit_remaining = 30
        self.rate_limit_reset = 0
    
    def _check_rate_limit(self):
        """Проверка и обработка лимита запросов"""
        if self.rate_limit_remaining <= 5:
            wait_time = max(self.rate_limit_reset - time.time(), 0) + 1
            print(f"Достигнут лимит запросов. Ожидание {wait_time:.0f} секунд...")
            time.sleep(wait_time)
            self._update_rate_limit()
    
    def _update_rate_limit(self):
        """Обновление информации о лимите запросов"""
        try:
            response = requests.get(f'{self.base_url}/rate_limit', headers=self.headers)
            if response.status_code == 200:
                rate_data = response.json()['resources']['core']
                self.rate_limit_remaining = rate_data['remaining']
                self.rate_limit_reset = rate_data['reset']
        except Exception as e:
            print(f"Ошибка при проверке лимита: {e}")
    
    def _make_request(self, url: str) -> Optional[Dict]:
        """Выполнение запроса к GitHub API"""
        self._check_rate_limit()
        try:
            response = requests.get(url, headers=self.headers)
            self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 30))
            self.rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print("Репозиторий не найден")
            elif response.status_code == 403:
                print("Доступ запрещен. Проверьте токен и лимиты")
            else:
                print(f"Ошибка API: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Ошибка запроса: {e}")
        return None
    
    def parse_github_url(self, url: str) -> Optional[tuple]:
        """Парсинг URL репозитория GitHub"""
        parsed = urlparse(url)
        if parsed.netloc not in ['github.com', 'www.github.com']:
            return None
        
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2:
            return path_parts[0], path_parts[1]
        return None
    
    def get_repo_info(self, owner: str, repo: str) -> Optional[GitHubRepoInfo]:
        """Получение основной информации о репозитории"""
        url = f'{self.base_url}/repos/{owner}/{repo}'
        data = self._make_request(url)
        
        if data:
            return GitHubRepoInfo(
                owner=owner,
                repo=repo,
                url=data['html_url'],
                description=data.get('description', ''),
                stars=data.get('stargazers_count', 0),
                forks=data.get('forks_count', 0),
                created_at=data.get('created_at', ''),
                updated_at=data.get('updated_at', '')
            )
        return None
    
    def get_files_list(self, owner: str, repo: str, path: str = '') -> List[Dict]:
        """Получение списка файлов и папок"""
        url = f'{self.base_url}/repos/{owner}/{repo}/contents/{path}'
        data = self._make_request(url)
        
        files = []
        folders = []
        
        if data and isinstance(data, list):
            for item in data:
                if item['type'] == 'file':
                    files.append({
                        'name': item['name'],
                        'path': item['path'],
                        'size': item.get('size', 0),
                        'download_url': item.get('download_url'),
                        'type': 'file'
                    })
                elif item['type'] == 'dir':
                    folders.append({
                        'name': item['name'],
                        'path': item['path'],
                        'type': 'dir'
                    })
        
        return files + folders
    
    def get_all_files_recursive(self, owner: str, repo: str, path: str = '') -> List[Dict]:
        """Рекурсивное получение всех файлов репозитория"""
        all_items = []
        current_items = self.get_files_list(owner, repo, path)
        
        for item in current_items:
            if item['type'] == 'dir':
                # Рекурсивно получаем содержимое папки
                sub_items = self.get_all_files_recursive(owner, repo, item['path'])
                all_items.extend(sub_items)
            else:
                all_items.append(item)
        
        return all_items
    
    def get_commits_list(self, owner: str, repo: str, limit: int = 30) -> List[CommitInfo]:
        """Получение списка коммитов"""
        url = f'{self.base_url}/repos/{owner}/{repo}/commits?per_page={limit}'
        data = self._make_request(url)
        
        commits = []
        if data and isinstance(data, list):
            for commit_data in data:
                commit = commit_data['commit']
                author = commit['author']['name'] if commit.get('author') else 'Unknown'
                
                commits.append(CommitInfo(
                    sha=commit_data['sha'][:7],
                    author=author,
                    message=commit['message'].split('\n')[0],  # Первая строка сообщения
                    date=commit['author']['date'] if commit.get('author') else '',
                    url=commit_data['html_url']
                ))
        
        return commits
    
    def get_folder_structure(self, owner: str, repo: str) -> Dict:
        """Получение структуры папок репозитория"""
        def build_tree(path: str = '') -> Dict:
            items = self.get_files_list(owner, repo, path)
            tree = {}
            
            for item in items:
                if item['type'] == 'dir':
                    tree[item['name']] = build_tree(item['path'])
                else:
                    tree[item['name']] = item
            
            return tree
        
        return build_tree()
    
    def analyze_repository(self, github_url: str) -> Dict[str, Any]:
        """Полный анализ репозитория"""
        parsed = self.parse_github_url(github_url)
        if not parsed:
            return {"error": "Invalid GitHub URL"}
        
        owner, repo = parsed
        print(f"Анализируем репозиторий: {owner}/{repo}")
        
        # Получаем основную информацию
        repo_info = self.get_repo_info(owner, repo)
        if not repo_info:
            return {"error": "Repository not found"}
        
        # Получаем коммиты
        print("Получаем список коммитов...")
        commits = self.get_commits_list(owner, repo, 10)
        
        # Получаем файлы
        print("Получаем список файлов...")
        files = self.get_all_files_recursive(owner, repo)
        
        # Анализируем типы файлов
        file_extensions = {}
        for file in files:
            if file['type'] == 'file':
                ext = os.path.splitext(file['name'])[1].lower()
                file_extensions[ext] = file_extensions.get(ext, 0) + 1
        
        # Группируем файлы по папкам
        files_by_folder = {}
        for file in files:
            folder = os.path.dirname(file['path'])
            if folder not in files_by_folder:
                files_by_folder[folder] = []
            files_by_folder[folder].append(file['name'])
        
        return {
            'repository_info': repo_info,
            'commits': commits,
            'total_files': len(files),
            'file_extensions': file_extensions,
            'files_by_folder': files_by_folder,
            'recent_commits_count': len(commits),
            'sample_files': files[:20]  # Первые 20 файлов для примера
        }

    def save_analysis_to_json(self, analysis_data: Dict, filename: str):
        """Сохранение результатов анализа в JSON файл"""
        # Конвертируем dataclass объекты в словари
        def convert_to_serializable(obj):
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            return obj
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, default=convert_to_serializable, 
                     indent=2, ensure_ascii=False)
        print(f"Анализ сохранен в файл: {filename}")

if __name__ == "__main__":
    analyzer = GitHubAnalyzer()
    github_url = "https://github.com/pascal65536/base_python_problems"
    analysis = analyzer.analyze_repository(github_url)
    if 'error' in analysis:
        print(f"Ошибка: {analysis['error']}")
        exit()
    
    repo_info = analysis['repository_info']
    print(f"\n=== ИНФОРМАЦИЯ О РЕПОЗИТОРИИ ===")
    print(f"Владелец: {repo_info.owner}")
    print(f"Репозиторий: {repo_info.repo}")
    print(f"Описание: {repo_info.description}")
    print(f"Звезды: {repo_info.stars}")
    print(f"Форки: {repo_info.forks}")
    print(f"Создан: {repo_info.created_at}")
    
    print(f"\n=== ПОСЛЕДНИЕ КОММИТЫ ===")
    for commit in analysis['commits']:
        print(f"{commit.sha} - {commit.author}: {commit.message}")
    
    print(f"\n=== СТАТИСТИКА ФАЙЛОВ ===")
    print(f"Всего файлов: {analysis['total_files']}")
    print("Расширения файлов:")
    for ext, count in analysis['file_extensions'].items():
        print(f"  {ext if ext else 'no extension'}: {count}")
    
    print(f"\n=== ПРИМЕР ФАЙЛОВ ===")
    for file in analysis['sample_files']:
        print(f"{file['path']} ({file['type']})")
    
    hash_url = behoof.str_to_md5(github_url)
    analyzer.save_analysis_to_json(analysis, f'github_analysis_{hash_url}.json')
    
    print(f"\nАнализ завершен! Лимит запросов осталось: {analyzer.rate_limit_remaining}")

