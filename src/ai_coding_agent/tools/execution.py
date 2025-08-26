"""Command execution tool."""

import asyncio
import subprocess
import shlex
import os
import signal
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from .base import BaseTool, ToolResult, ToolResultStatus


class ExecutionTool(BaseTool):
    """Tool for executing commands, running tests, and building projects."""
    
    def __init__(self):
        super().__init__()
        self.name = "execution"
        self.running_processes: Dict[str, subprocess.Popen] = {}
    
    @property
    def description(self) -> str:
        return "Execute commands, run tests, build projects, and manage processes"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["run", "test", "build", "install", "start", "stop", "status"],
                    "description": "The execution operation to perform"
                },
                "command": {
                    "type": "string",
                    "description": "Command to execute"
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command arguments"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Working directory for command execution"
                },
                "environment": {
                    "type": "object",
                    "description": "Environment variables to set"
                },
                "timeout": {
                    "type": "integer",
                    "default": 300,
                    "description": "Timeout in seconds"
                },
                "capture_output": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to capture command output"
                },
                "background": {
                    "type": "boolean",
                    "default": False,
                    "description": "Run command in background"
                },
                "process_id": {
                    "type": "string",
                    "description": "Process ID for stop/status operations"
                }
            },
            "required": ["operation"]
        }
    
    def is_safe_operation(self, **kwargs) -> bool:
        """Check if operation is safe."""
        operation = kwargs.get("operation", "")
        command = kwargs.get("command", "")
        
        # Test and status operations are generally safe
        if operation in ["test", "status"]:
            return True
        
        # Dangerous commands require approval
        dangerous_commands = [
            "rm", "rmdir", "del", "format", "fdisk",
            "dd", "mkfs", "sudo", "su", "chmod 777",
            "wget", "curl", "git push", "docker run",
            "npm publish", "pip install", "apt install"
        ]
        
        if any(dangerous in command.lower() for dangerous in dangerous_commands):
            return False
        
        # Build and install operations may require approval
        if operation in ["build", "install", "start"]:
            return False
        
        return True
    
    def get_preview(self, **kwargs) -> str:
        """Get operation preview."""
        operation = kwargs.get("operation", "")
        command = kwargs.get("command", "")
        args = kwargs.get("args", [])
        working_dir = kwargs.get("working_directory", ".")
        
        if operation == "run":
            full_command = f"{command} {' '.join(args)}" if args else command
            return f"Execute: {full_command} (in {working_dir})"
        elif operation == "test":
            return f"Run tests: {command or 'default test command'}"
        elif operation == "build":
            return f"Build project: {command or 'default build command'}"
        elif operation == "install":
            return f"Install dependencies: {command or 'default install command'}"
        elif operation == "start":
            return f"Start service: {command}"
        elif operation == "stop":
            process_id = kwargs.get("process_id", "")
            return f"Stop process: {process_id}"
        else:
            return f"Execute {operation}"
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the operation."""
        operation = kwargs.get("operation")
        
        try:
            if operation == "run":
                return await self._run_command(**kwargs)
            elif operation == "test":
                return await self._run_tests(**kwargs)
            elif operation == "build":
                return await self._build_project(**kwargs)
            elif operation == "install":
                return await self._install_dependencies(**kwargs)
            elif operation == "start":
                return await self._start_service(**kwargs)
            elif operation == "stop":
                return await self._stop_process(**kwargs)
            elif operation == "status":
                return await self._get_process_status(**kwargs)
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"Unknown execution operation: {operation}"
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=str(e),
                suggested_actions=[
                    "Check command syntax",
                    "Verify working directory exists",
                    "Check system permissions"
                ]
            )
    
    async def _run_command(self, **kwargs) -> ToolResult:
        """Run a generic command."""
        command = kwargs.get("command", "")
        args = kwargs.get("args", [])
        working_dir = kwargs.get("working_directory", ".")
        environment = kwargs.get("environment", {})
        timeout = kwargs.get("timeout", 300)
        capture_output = kwargs.get("capture_output", True)
        background = kwargs.get("background", False)
        
        if not command:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="Command is required"
            )
        
        # Prepare the full command
        if args:
            full_command = [command] + args
        else:
            # Parse command string
            full_command = shlex.split(command)
        
        # Set up environment
        env = os.environ.copy()
        env.update(environment)
        
        # Validate working directory
        if not Path(working_dir).exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Working directory does not exist: {working_dir}"
            )
        
        try:
            if background:
                return await self._run_background_process(full_command, working_dir, env, timeout)
            else:
                return await self._run_foreground_process(full_command, working_dir, env, timeout, capture_output)
        
        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Command timed out after {timeout} seconds",
                suggested_actions=["Increase timeout", "Check if command is hanging"]
            )
        except FileNotFoundError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Command not found: {command}",
                suggested_actions=[f"Install {command}", "Check PATH environment variable"]
            )
    
    async def _run_foreground_process(
        self, 
        command: List[str], 
        working_dir: str, 
        env: Dict[str, str], 
        timeout: int,
        capture_output: bool
    ) -> ToolResult:
        """Run a command in the foreground."""
        
        if capture_output:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=working_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ""
                stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ""
                
                return ToolResult(
                    status=ToolResultStatus.SUCCESS if process.returncode == 0 else ToolResultStatus.ERROR,
                    content=stdout_text or stderr_text,
                    data={
                        "command": " ".join(command),
                        "return_code": process.returncode,
                        "stdout": stdout_text,
                        "stderr": stderr_text,
                        "working_directory": working_dir
                    },
                    error=stderr_text if process.returncode != 0 else None
                )
            
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise subprocess.TimeoutExpired(" ".join(command), timeout)
        
        else:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=working_dir,
                env=env
            )
            
            try:
                return_code = await asyncio.wait_for(
                    process.wait(),
                    timeout=timeout
                )
                
                return ToolResult(
                    status=ToolResultStatus.SUCCESS if return_code == 0 else ToolResultStatus.ERROR,
                    content=f"Command completed with return code {return_code}",
                    data={
                        "command": " ".join(command),
                        "return_code": return_code,
                        "working_directory": working_dir
                    }
                )
            
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise subprocess.TimeoutExpired(" ".join(command), timeout)
    
    async def _run_background_process(
        self, 
        command: List[str], 
        working_dir: str, 
        env: Dict[str, str], 
        timeout: int
    ) -> ToolResult:
        """Run a command in the background."""
        
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=working_dir,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Generate a process ID for tracking
        process_id = f"proc_{process.pid}_{len(self.running_processes)}"
        self.running_processes[process_id] = process
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            content=f"Started background process: {' '.join(command)}",
            data={
                "process_id": process_id,
                "pid": process.pid,
                "command": " ".join(command),
                "working_directory": working_dir
            }
        )
    
    async def _run_tests(self, **kwargs) -> ToolResult:
        """Run project tests."""
        working_dir = kwargs.get("working_directory", ".")
        command = kwargs.get("command")
        
        # Auto-detect test framework if no command specified
        if not command:
            command = self._detect_test_command(working_dir)
        
        if not command:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="No test command found",
                suggested_actions=[
                    "Specify test command explicitly",
                    "Check if test framework is installed",
                    "Verify test files exist"
                ]
            )
        
        # Run the test command
        test_kwargs = kwargs.copy()
        test_kwargs["command"] = command
        test_kwargs["operation"] = "run"
        
        result = await self._run_command(**test_kwargs)
        
        # Enhance result with test-specific information
        if result.status == ToolResultStatus.SUCCESS:
            result.content = f"Tests passed: {result.content}"
        else:
            result.content = f"Tests failed: {result.content}"
        
        return result
    
    async def _build_project(self, **kwargs) -> ToolResult:
        """Build the project."""
        working_dir = kwargs.get("working_directory", ".")
        command = kwargs.get("command")
        
        # Auto-detect build command if no command specified
        if not command:
            command = self._detect_build_command(working_dir)
        
        if not command:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="No build command found",
                suggested_actions=[
                    "Specify build command explicitly",
                    "Check if build tools are installed",
                    "Verify build configuration exists"
                ]
            )
        
        # Run the build command
        build_kwargs = kwargs.copy()
        build_kwargs["command"] = command
        build_kwargs["operation"] = "run"
        
        result = await self._run_command(**build_kwargs)
        
        # Enhance result with build-specific information
        if result.status == ToolResultStatus.SUCCESS:
            result.content = f"Build successful: {result.content}"
        else:
            result.content = f"Build failed: {result.content}"
        
        return result
    
    async def _install_dependencies(self, **kwargs) -> ToolResult:
        """Install project dependencies."""
        working_dir = kwargs.get("working_directory", ".")
        command = kwargs.get("command")
        
        # Auto-detect install command if no command specified
        if not command:
            command = self._detect_install_command(working_dir)
        
        if not command:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="No install command found",
                suggested_actions=[
                    "Specify install command explicitly",
                    "Check if package manager is installed",
                    "Verify dependency file exists"
                ]
            )
        
        # Run the install command
        install_kwargs = kwargs.copy()
        install_kwargs["command"] = command
        install_kwargs["operation"] = "run"
        
        result = await self._run_command(**install_kwargs)
        
        # Enhance result with install-specific information
        if result.status == ToolResultStatus.SUCCESS:
            result.content = f"Dependencies installed: {result.content}"
        else:
            result.content = f"Installation failed: {result.content}"
        
        return result
    
    async def _start_service(self, **kwargs) -> ToolResult:
        """Start a service or application."""
        command = kwargs.get("command", "")
        
        if not command:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="Service command is required"
            )
        
        # Start as background process
        service_kwargs = kwargs.copy()
        service_kwargs["background"] = True
        service_kwargs["operation"] = "run"
        
        return await self._run_command(**service_kwargs)
    
    async def _stop_process(self, **kwargs) -> ToolResult:
        """Stop a running background process."""
        process_id = kwargs.get("process_id", "")
        
        if not process_id:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="Process ID is required"
            )
        
        if process_id not in self.running_processes:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Process not found: {process_id}",
                suggested_actions=["Check process ID", "Use status operation to list processes"]
            )
        
        process = self.running_processes[process_id]
        
        try:
            # Try graceful termination first
            process.terminate()
            
            # Wait for termination
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                # Force kill if graceful termination fails
                process.kill()
                await process.wait()
            
            # Remove from tracking
            del self.running_processes[process_id]
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Process stopped: {process_id}",
                data={
                    "process_id": process_id,
                    "pid": process.pid
                }
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to stop process: {str(e)}"
            )
    
    async def _get_process_status(self, **kwargs) -> ToolResult:
        """Get status of running processes."""
        process_id = kwargs.get("process_id")
        
        if process_id:
            # Get status of specific process
            if process_id not in self.running_processes:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"Process not found: {process_id}"
                )
            
            process = self.running_processes[process_id]
            is_running = process.poll() is None
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Process {process_id} is {'running' if is_running else 'stopped'}",
                data={
                    "process_id": process_id,
                    "pid": process.pid,
                    "is_running": is_running,
                    "return_code": process.returncode
                }
            )
        else:
            # Get status of all processes
            processes_status = []
            
            for pid, process in list(self.running_processes.items()):
                is_running = process.poll() is None
                processes_status.append({
                    "process_id": pid,
                    "pid": process.pid,
                    "is_running": is_running,
                    "return_code": process.returncode
                })
                
                # Clean up stopped processes
                if not is_running:
                    del self.running_processes[pid]
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Found {len(processes_status)} tracked processes",
                data={
                    "processes": processes_status,
                    "total_count": len(processes_status)
                }
            )
    
    def _detect_test_command(self, working_dir: str) -> Optional[str]:
        """Auto-detect test command based on project files."""
        project_path = Path(working_dir)
        
        # Python projects
        if (project_path / "pytest.ini").exists() or (project_path / "setup.cfg").exists():
            return "pytest"
        elif (project_path / "test").exists() and any(project_path.glob("test*.py")):
            return "python -m pytest"
        elif any(project_path.glob("**/test*.py")):
            return "python -m unittest discover"
        
        # Node.js projects
        elif (project_path / "package.json").exists():
            return "npm test"
        
        # Java projects
        elif (project_path / "pom.xml").exists():
            return "mvn test"
        elif (project_path / "build.gradle").exists():
            return "gradle test"
        
        # Rust projects
        elif (project_path / "Cargo.toml").exists():
            return "cargo test"
        
        # Go projects
        elif any(project_path.glob("*.go")):
            return "go test"
        
        return None
    
    def _detect_build_command(self, working_dir: str) -> Optional[str]:
        """Auto-detect build command based on project files."""
        project_path = Path(working_dir)
        
        # Python projects
        if (project_path / "setup.py").exists():
            return "python setup.py build"
        elif (project_path / "pyproject.toml").exists():
            return "python -m build"
        
        # Node.js projects
        elif (project_path / "package.json").exists():
            return "npm run build"
        
        # Java projects
        elif (project_path / "pom.xml").exists():
            return "mvn compile"
        elif (project_path / "build.gradle").exists():
            return "gradle build"
        
        # Rust projects
        elif (project_path / "Cargo.toml").exists():
            return "cargo build"
        
        # Go projects
        elif any(project_path.glob("*.go")):
            return "go build"
        
        # C/C++ projects
        elif (project_path / "Makefile").exists():
            return "make"
        elif (project_path / "CMakeLists.txt").exists():
            return "cmake --build ."
        
        return None
    
    def _detect_install_command(self, working_dir: str) -> Optional[str]:
        """Auto-detect install command based on project files."""
        project_path = Path(working_dir)
        
        # Python projects
        if (project_path / "requirements.txt").exists():
            return "pip install -r requirements.txt"
        elif (project_path / "pyproject.toml").exists():
            return "pip install ."
        elif (project_path / "setup.py").exists():
            return "pip install ."
        
        # Node.js projects
        elif (project_path / "package.json").exists():
            if (project_path / "package-lock.json").exists():
                return "npm ci"
            else:
                return "npm install"
        
        # Rust projects
        elif (project_path / "Cargo.toml").exists():
            return "cargo build"
        
        # Go projects
        elif (project_path / "go.mod").exists():
            return "go mod download"
        
        return None