"""Code analysis and quality tool."""

import ast
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from .base import BaseTool, ToolResult, ToolResultStatus


class CodeAnalysisTool(BaseTool):
    """Tool for code analysis and quality checks."""
    
    def __init__(self):
        super().__init__()
        self.name = "code_analysis"
    
    @property
    def description(self) -> str:
        return "Analyze code quality, run linters, find dependencies, and check for issues"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["lint", "dependencies", "complexity", "security", "structure", "imports", "functions", "classes"],
                    "description": "The analysis operation to perform"
                },
                "path": {
                    "type": "string",
                    "description": "File or directory path to analyze"
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "typescript", "auto"],
                    "default": "auto",
                    "description": "Programming language to analyze"
                },
                "tool": {
                    "type": "string",
                    "enum": ["flake8", "pylint", "black", "eslint", "tsc", "auto"],
                    "default": "auto",
                    "description": "Specific tool to use for analysis"
                },
                "fix": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to attempt automatic fixes"
                }
            },
            "required": ["operation", "path"]
        }
    
    def is_safe_operation(self, **kwargs) -> bool:
        """Check if operation is safe."""
        # Analysis operations are generally safe
        # Only auto-fix requires approval
        return not kwargs.get("fix", False)
    
    def get_preview(self, **kwargs) -> str:
        """Get operation preview."""
        operation = kwargs.get("operation", "")
        path = kwargs.get("path", "")
        fix = kwargs.get("fix", False)
        
        if fix:
            return f"Analyze {path} with {operation} and apply automatic fixes"
        else:
            return f"Analyze {path} with {operation}"
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute code analysis operation."""
        operation = kwargs.get("operation")
        path = kwargs.get("path")
        language = kwargs.get("language", "auto")
        tool = kwargs.get("tool", "auto")
        fix = kwargs.get("fix", False)
        
        try:
            if operation == "lint":
                return await self._run_linter(path, language, tool, fix)
            elif operation == "dependencies":
                return await self._analyze_dependencies(path, language)
            elif operation == "complexity":
                return await self._analyze_complexity(path, language)
            elif operation == "security":
                return await self._security_scan(path, language)
            elif operation == "structure":
                return await self._analyze_structure(path, language)
            elif operation == "imports":
                return await self._analyze_imports(path)
            elif operation == "functions":
                return await self._analyze_functions(path)
            elif operation == "classes":
                return await self._analyze_classes(path)
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"Unknown analysis operation: {operation}"
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=str(e),
                suggested_actions=[
                    "Check if the file exists",
                    "Verify the file is valid code",
                    "Install required analysis tools"
                ]
            )
    
    async def _run_linter(self, path: str, language: str, tool: str, fix: bool) -> ToolResult:
        """Run code linter."""
        file_path = Path(path)
        
        if not file_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"File not found: {path}"
            )
        
        # Auto-detect language if needed
        if language == "auto":
            language = self._detect_language(file_path)
        
        # Auto-select tool if needed
        if tool == "auto":
            tool = self._select_linter(language)
        
        issues = []
        
        try:
            if language == "python":
                if tool == "flake8":
                    issues = await self._run_flake8(file_path, fix)
                elif tool == "pylint":
                    issues = await self._run_pylint(file_path)
                elif tool == "black":
                    issues = await self._run_black(file_path, fix)
                else:
                    # Try multiple Python tools
                    issues.extend(await self._run_flake8(file_path, fix))
            elif language in ["javascript", "typescript"]:
                if tool == "eslint":
                    issues = await self._run_eslint(file_path, fix)
                elif tool == "tsc" and language == "typescript":
                    issues = await self._run_typescript_check(file_path)
            
            severity_counts = {"error": 0, "warning": 0, "info": 0}
            for issue in issues:
                severity_counts[issue.get("severity", "info")] += 1
            
            if not issues:
                content = f"No linting issues found in {path}"
            else:
                content = f"Found {len(issues)} issues: {severity_counts['error']} errors, {severity_counts['warning']} warnings"
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=content,
                data={
                    "issues": issues,
                    "severity_counts": severity_counts,
                    "tool": tool,
                    "language": language,
                    "fixed": fix
                }
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Linting failed: {str(e)}",
                suggested_actions=[f"Install {tool}", "Check file syntax"]
            )
    
    async def _run_flake8(self, file_path: Path, fix: bool = False) -> List[Dict[str, Any]]:
        """Run flake8 linter."""
        issues = []
        try:
            result = subprocess.run(
                ["flake8", "--format=json", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            issue_data = json.loads(line)
                            issues.append({
                                "file": issue_data.get("filename"),
                                "line": issue_data.get("line_number"),
                                "column": issue_data.get("column_number"),
                                "code": issue_data.get("code"),
                                "message": issue_data.get("text"),
                                "severity": "error" if issue_data.get("code", "").startswith("E") else "warning"
                            })
                        except json.JSONDecodeError:
                            continue
        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            # flake8 not installed
            pass
        
        return issues
    
    async def _run_pylint(self, file_path: Path) -> List[Dict[str, Any]]:
        """Run pylint linter."""
        issues = []
        try:
            result = subprocess.run(
                ["pylint", "--output-format=json", str(file_path)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.stdout:
                try:
                    pylint_data = json.loads(result.stdout)
                    for issue in pylint_data:
                        issues.append({
                            "file": issue.get("path"),
                            "line": issue.get("line"),
                            "column": issue.get("column"),
                            "code": issue.get("symbol"),
                            "message": issue.get("message"),
                            "severity": issue.get("type", "info").lower()
                        })
                except json.JSONDecodeError:
                    pass
        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            # pylint not installed
            pass
        
        return issues
    
    async def _run_black(self, file_path: Path, fix: bool = False) -> List[Dict[str, Any]]:
        """Run black formatter."""
        issues = []
        try:
            # Check if file needs formatting
            result = subprocess.run(
                ["black", "--check", "--diff", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                issues.append({
                    "file": str(file_path),
                    "line": 0,
                    "column": 0,
                    "code": "black",
                    "message": "File needs formatting",
                    "severity": "warning"
                })
                
                if fix:
                    # Apply formatting
                    subprocess.run(
                        ["black", str(file_path)],
                        capture_output=True,
                        timeout=30
                    )
                    issues[-1]["message"] = "File formatted successfully"
        
        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            # black not installed
            pass
        
        return issues
    
    async def _run_eslint(self, file_path: Path, fix: bool = False) -> List[Dict[str, Any]]:
        """Run ESLint."""
        issues = []
        try:
            cmd = ["eslint", "--format=json", str(file_path)]
            if fix:
                cmd.append("--fix")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                try:
                    eslint_data = json.loads(result.stdout)
                    for file_result in eslint_data:
                        for message in file_result.get("messages", []):
                            issues.append({
                                "file": file_result.get("filePath"),
                                "line": message.get("line"),
                                "column": message.get("column"),
                                "code": message.get("ruleId"),
                                "message": message.get("message"),
                                "severity": message.get("severity") == 2 and "error" or "warning"
                            })
                except json.JSONDecodeError:
                    pass
        
        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            # eslint not installed
            pass
        
        return issues
    
    async def _run_typescript_check(self, file_path: Path) -> List[Dict[str, Any]]:
        """Run TypeScript compiler check."""
        issues = []
        try:
            result = subprocess.run(
                ["tsc", "--noEmit", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stderr:
                for line in result.stderr.strip().split('\n'):
                    if "error TS" in line:
                        parts = line.split(':')
                        if len(parts) >= 4:
                            issues.append({
                                "file": str(file_path),
                                "line": int(parts[1]) if parts[1].isdigit() else 0,
                                "column": int(parts[2]) if parts[2].isdigit() else 0,
                                "code": "typescript",
                                "message": ':'.join(parts[3:]).strip(),
                                "severity": "error"
                            })
        
        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            # TypeScript not installed
            pass
        
        return issues
    
    async def _analyze_dependencies(self, path: str, language: str) -> ToolResult:
        """Analyze project dependencies."""
        file_path = Path(path)
        dependencies = []
        
        if language == "auto":
            language = self._detect_language(file_path)
        
        try:
            if language == "python":
                # Look for requirements.txt, setup.py, pyproject.toml
                project_root = file_path if file_path.is_dir() else file_path.parent
                
                requirements_file = project_root / "requirements.txt"
                if requirements_file.exists():
                    with open(requirements_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                dependencies.append({
                                    "name": line.split('==')[0].split('>=')[0].split('<=')[0],
                                    "version": line,
                                    "source": "requirements.txt"
                                })
                
                # Also check imports in Python files
                if file_path.suffix == '.py':
                    imports = await self._extract_python_imports(file_path)
                    for imp in imports:
                        dependencies.append({
                            "name": imp,
                            "version": "unknown",
                            "source": "import"
                        })
            
            elif language in ["javascript", "typescript"]:
                # Look for package.json
                project_root = file_path if file_path.is_dir() else file_path.parent
                package_json = project_root / "package.json"
                
                if package_json.exists():
                    with open(package_json, 'r') as f:
                        package_data = json.load(f)
                        
                        for dep_type in ["dependencies", "devDependencies"]:
                            for name, version in package_data.get(dep_type, {}).items():
                                dependencies.append({
                                    "name": name,
                                    "version": version,
                                    "source": dep_type
                                })
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Found {len(dependencies)} dependencies",
                data={
                    "dependencies": dependencies,
                    "language": language,
                    "total_count": len(dependencies)
                }
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Dependency analysis failed: {str(e)}"
            )
    
    async def _analyze_complexity(self, path: str, language: str) -> ToolResult:
        """Analyze code complexity."""
        file_path = Path(path)
        
        if not file_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"File not found: {path}"
            )
        
        if language == "auto":
            language = self._detect_language(file_path)
        
        try:
            if language == "python" and file_path.suffix == '.py':
                return await self._analyze_python_complexity(file_path)
            else:
                return await self._analyze_generic_complexity(file_path)
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Complexity analysis failed: {str(e)}"
            )
    
    async def _analyze_python_complexity(self, file_path: Path) -> ToolResult:
        """Analyze Python code complexity using AST."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Syntax error in Python file: {str(e)}"
            )
        
        complexity_data = {
            "functions": [],
            "classes": [],
            "total_lines": len(content.splitlines()),
            "total_functions": 0,
            "total_classes": 0,
            "avg_function_length": 0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity_data["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "length": getattr(node, 'end_lineno', node.lineno) - node.lineno + 1,
                    "args": len(node.args.args),
                    "complexity": self._calculate_cyclomatic_complexity(node)
                })
                complexity_data["total_functions"] += 1
            
            elif isinstance(node, ast.ClassDef):
                methods = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]
                complexity_data["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "length": getattr(node, 'end_lineno', node.lineno) - node.lineno + 1,
                    "methods": len(methods)
                })
                complexity_data["total_classes"] += 1
        
        if complexity_data["functions"]:
            complexity_data["avg_function_length"] = sum(
                f["length"] for f in complexity_data["functions"]
            ) / len(complexity_data["functions"])
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            content=f"Analyzed {complexity_data['total_functions']} functions and {complexity_data['total_classes']} classes",
            data=complexity_data
        )
    
    def _calculate_cyclomatic_complexity(self, node) -> int:
        """Calculate cyclomatic complexity for a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    async def _analyze_generic_complexity(self, file_path: Path) -> ToolResult:
        """Analyze complexity for non-Python files."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.splitlines()
        complexity_data = {
            "total_lines": len(lines),
            "non_empty_lines": len([line for line in lines if line.strip()]),
            "comment_lines": 0,
            "function_count": 0,
            "complexity_indicators": 0
        }
        
        # Count comments and complexity indicators
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('#') or stripped.startswith('/*'):
                complexity_data["comment_lines"] += 1
            
            # Count complexity indicators
            if any(keyword in stripped for keyword in ['if', 'for', 'while', 'switch', 'try', 'catch']):
                complexity_data["complexity_indicators"] += 1
            
            if any(keyword in stripped for keyword in ['function', 'def', 'async def', 'method']):
                complexity_data["function_count"] += 1
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            content=f"Analyzed {complexity_data['total_lines']} lines with {complexity_data['function_count']} functions",
            data=complexity_data
        )
    
    async def _security_scan(self, path: str, language: str) -> ToolResult:
        """Basic security scan."""
        file_path = Path(path)
        
        if not file_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"File not found: {path}"
            )
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        security_issues = []
        
        # Common security patterns to check
        security_patterns = {
            "hardcoded_password": ["password", "pwd", "passwd"],
            "hardcoded_key": ["api_key", "secret_key", "private_key"],
            "sql_injection": ["execute(", "query(", "raw("],
            "eval_usage": ["eval(", "exec("],
            "insecure_random": ["random.random(", "Math.random()"],
        }
        
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            for issue_type, patterns in security_patterns.items():
                for pattern in patterns:
                    if pattern in line_lower and "=" in line:
                        security_issues.append({
                            "type": issue_type,
                            "line": i,
                            "content": line.strip(),
                            "severity": "medium",
                            "description": f"Potential {issue_type.replace('_', ' ')} detected"
                        })
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            content=f"Security scan found {len(security_issues)} potential issues",
            data={
                "issues": security_issues,
                "total_issues": len(security_issues),
                "file_analyzed": str(file_path)
            }
        )
    
    async def _analyze_structure(self, path: str, language: str) -> ToolResult:
        """Analyze code structure."""
        file_path = Path(path)
        
        if file_path.is_dir():
            return await self._analyze_project_structure(file_path)
        else:
            return await self._analyze_file_structure(file_path, language)
    
    async def _analyze_project_structure(self, dir_path: Path) -> ToolResult:
        """Analyze project directory structure."""
        structure = {
            "directories": [],
            "files": [],
            "file_types": {},
            "total_files": 0,
            "total_directories": 0
        }
        
        for item in dir_path.rglob("*"):
            if item.is_file():
                structure["files"].append({
                    "path": str(item.relative_to(dir_path)),
                    "size": item.stat().st_size,
                    "extension": item.suffix
                })
                structure["total_files"] += 1
                
                # Count file types
                ext = item.suffix or "no_extension"
                structure["file_types"][ext] = structure["file_types"].get(ext, 0) + 1
            
            elif item.is_dir():
                structure["directories"].append(str(item.relative_to(dir_path)))
                structure["total_directories"] += 1
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            content=f"Project contains {structure['total_files']} files in {structure['total_directories']} directories",
            data=structure
        )
    
    async def _analyze_file_structure(self, file_path: Path, language: str) -> ToolResult:
        """Analyze individual file structure."""
        if language == "auto":
            language = self._detect_language(file_path)
        
        if language == "python":
            return await self._analyze_functions(str(file_path))
        else:
            return await self._analyze_generic_complexity(file_path)
    
    async def _analyze_imports(self, path: str) -> ToolResult:
        """Analyze imports in the file."""
        file_path = Path(path)
        
        if not file_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"File not found: {path}"
            )
        
        language = self._detect_language(file_path)
        
        if language == "python":
            imports = await self._extract_python_imports(file_path)
        else:
            imports = await self._extract_generic_imports(file_path)
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            content=f"Found {len(imports)} imports",
            data={
                "imports": imports,
                "language": language,
                "total_count": len(imports)
            }
        )
    
    async def _extract_python_imports(self, file_path: Path) -> List[str]:
        """Extract Python imports."""
        imports = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        
        except SyntaxError:
            # Fallback to regex parsing
            import re
            lines = content.splitlines()
            for line in lines:
                if line.strip().startswith(('import ', 'from ')):
                    match = re.match(r'^(?:from\s+(\S+)\s+)?import\s+(.+)', line.strip())
                    if match:
                        module = match.group(1) or match.group(2).split()[0]
                        imports.append(module)
        
        return list(set(imports))  # Remove duplicates
    
    async def _extract_generic_imports(self, file_path: Path) -> List[str]:
        """Extract imports from non-Python files."""
        imports = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.splitlines()
        for line in lines:
            stripped = line.strip()
            # JavaScript/TypeScript imports
            if stripped.startswith('import ') or stripped.startswith('const ') and 'require(' in stripped:
                imports.append(stripped)
            # Java imports
            elif stripped.startswith('import ') and stripped.endswith(';'):
                imports.append(stripped)
            # C/C++ includes
            elif stripped.startswith('#include'):
                imports.append(stripped)
        
        return imports
    
    async def _analyze_functions(self, path: str) -> ToolResult:
        """Analyze functions in the file."""
        file_path = Path(path)
        
        if not file_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"File not found: {path}"
            )
        
        language = self._detect_language(file_path)
        
        if language == "python":
            return await self._analyze_python_complexity(file_path)
        else:
            # Generic function analysis
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.splitlines()
            functions = []
            
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if any(keyword in stripped for keyword in ['function ', 'def ', 'async def', 'method ']):
                    functions.append({
                        "line": i,
                        "content": stripped,
                        "type": "function"
                    })
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Found {len(functions)} functions",
                data={
                    "functions": functions,
                    "total_count": len(functions),
                    "language": language
                }
            )
    
    async def _analyze_classes(self, path: str) -> ToolResult:
        """Analyze classes in the file."""
        file_path = Path(path)
        
        if not file_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"File not found: {path}"
            )
        
        language = self._detect_language(file_path)
        
        if language == "python":
            result = await self._analyze_python_complexity(file_path)
            if result.status == ToolResultStatus.SUCCESS:
                classes = result.data.get("classes", [])
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    content=f"Found {len(classes)} classes",
                    data={
                        "classes": classes,
                        "total_count": len(classes),
                        "language": language
                    }
                )
            return result
        else:
            # Generic class analysis
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.splitlines()
            classes = []
            
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if any(keyword in stripped for keyword in ['class ', 'interface ', 'struct ']):
                    classes.append({
                        "line": i,
                        "content": stripped,
                        "type": "class"
                    })
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Found {len(classes)} classes",
                data={
                    "classes": classes,
                    "total_count": len(classes),
                    "language": language
                }
            )
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext = file_path.suffix.lower()
        
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust'
        }
        
        return extension_map.get(ext, 'unknown')
    
    def _select_linter(self, language: str) -> str:
        """Select appropriate linter for language."""
        linter_map = {
            'python': 'flake8',
            'javascript': 'eslint',
            'typescript': 'eslint'
        }
        
        return linter_map.get(language, 'auto')