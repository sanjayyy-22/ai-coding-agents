# AI Coding Agent - Demo Usage Examples

This file contains example interactions demonstrating the AI Coding Agent's capabilities.

## 🚀 Getting Started

### First Run
```bash
# Start the agent
agent start

# First interaction
💬 You: Hello! What can you help me with?

🤖 Agent: Hello! I'm your AI Coding Agent, here to help with development tasks. I can:

📁 **File Operations**: Read, write, search, and manage files
🔧 **Git Integration**: Handle version control tasks
🔍 **Code Analysis**: Lint, analyze dependencies, check complexity
⚡ **Command Execution**: Run tests, builds, and other commands safely
🧠 **Learning**: Remember your preferences and improve over time

What would you like to work on today?
```

## 📁 File Operations

### Reading and Analyzing Files
```bash
💬 You: What's in my package.json file?

🤖 Agent: I'll read your package.json file for you.

🔧 [filesystem] Reading package.json...

Your package.json contains:
- **Name**: my-project
- **Version**: 1.0.0
- **Dependencies**: 
  - express: ^4.18.0
  - lodash: ^4.17.21
- **Dev Dependencies**:
  - jest: ^29.0.0
  - nodemon: ^3.0.0
- **Scripts**:
  - start: node index.js
  - test: jest
  - dev: nodemon index.js

Would you like me to analyze any specific aspect of your dependencies?
```

### Code Analysis
```bash
💬 You: Check my auth.js file for security issues

🤖 Agent: I'll perform a security analysis on your auth.js file.

🔧 [code_analysis] Running security scan on auth.js...
🔧 [code_analysis] Analyzing dependencies...

**Security Analysis Results:**

⚠️  **Medium Risk Issues Found:**
1. **Line 23**: Hardcoded secret key detected
   - Consider using environment variables
2. **Line 45**: No rate limiting on login endpoint
   - Add rate limiting to prevent brute force attacks
3. **Line 67**: Password stored in plain text logs
   - Remove sensitive data from logs

✅ **Good Practices Found:**
- Password hashing with bcrypt
- Input validation present
- HTTPS enforced

Would you like me to fix these security issues?
```

## 🔧 Git Operations

### Repository Status and Management
```bash
💬 You: What's the status of my git repository?

🤖 Agent: Let me check your git repository status.

🔧 [git] Getting repository status...

**Git Status:**
- **Branch**: feature/user-auth
- **Modified files**: 3
  - src/auth.js (modified)
  - tests/auth.test.js (modified)
  - package.json (modified)
- **Untracked files**: 1
  - src/middleware/validation.js (new file)
- **Repository state**: Clean working tree except for above changes

Your recent work looks like authentication feature development. Would you like me to:
1. Review the changes before committing
2. Create a commit with an appropriate message
3. Check for any issues in the modified files
```

### Commit Management
```bash
💬 You: Review my changes and create a commit if they look good

🤖 Agent: I'll review your changes and prepare a commit.

🔧 [git] Getting diff for modified files...
🔧 [code_analysis] Analyzing changed code...
🔧 [execution] Running tests...

**Change Review:**

**✅ src/auth.js**
- Added JWT token generation
- Improved error handling
- Security: Good use of environment variables

**✅ tests/auth.test.js**  
- Added comprehensive test coverage
- Tests for both success and failure cases
- Good use of mocking

**✅ package.json**
- Added jsonwebtoken dependency
- Version looks appropriate

**⚠️ src/middleware/validation.js**
- New validation middleware
- Consider adding tests for this file

**Test Results**: ✅ All tests passing (15/15)

**Suggested Commit Message:**
```
feat: implement JWT authentication with comprehensive validation

- Add JWT token generation and validation
- Implement middleware for request validation  
- Add comprehensive test coverage for auth flows
- Update dependencies to include jsonwebtoken

Tests: 15/15 passing
```

Shall I proceed with this commit? [y/N]
```

## ⚡ Command Execution

### Running Tests and Fixing Issues
```bash
💬 You: Run the tests and fix any failures

🤖 Agent: I'll run your test suite and address any issues found.

🔧 [execution] Running test command: npm test...

**Test Results:**
```
FAIL tests/api.test.js
  ● POST /api/users › should create user with valid data
    expect(received).toBe(expected) // Object.is equality
    Expected: 201
    Received: 400
    
    ValidationError: email is required
```

❌ **1 test failing**

🔧 [filesystem] Reading tests/api.test.js to understand the failure...
🔧 [filesystem] Reading src/api/users.js to check validation logic...

**Issue Found:** Test is missing email field in request body.

🔧 [filesystem] Fixing test case...

**Fixed test case:**
```javascript
// Before
const userData = { name: 'John Doe', age: 30 };

// After  
const userData = { 
  name: 'John Doe', 
  email: 'john@example.com',
  age: 30 
};
```

🔧 [execution] Re-running tests...

✅ **All tests now passing!** (12/12)

The issue was a missing required field in the test data. I've updated the test to include the email field that the validation middleware expects.
```

### Project Setup
```bash
💬 You: Set up a new FastAPI project with authentication and testing

🤖 Agent: I'll help you set up a complete FastAPI project with authentication and testing infrastructure.

🔧 [filesystem] Creating project structure...
🔧 [filesystem] Creating requirements.txt...
🔧 [filesystem] Creating main.py...
🔧 [filesystem] Creating auth module...
🔧 [filesystem] Creating test configuration...
🔧 [execution] Installing dependencies...

**Project Structure Created:**
```
fastapi-project/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── router.py        # Auth endpoints
│   │   ├── models.py        # User models
│   │   └── utils.py         # JWT utilities
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration
│   │   └── security.py      # Security utilities
│   └── database/
│       ├── __init__.py
│       └── models.py        # Database models
├── tests/
│   ├── __init__.py
│   ├── test_auth.py         # Auth tests
│   └── conftest.py          # Test configuration
├── requirements.txt
├── .env.example
└── README.md
```

**Features Implemented:**
✅ JWT Authentication with refresh tokens
✅ User registration and login endpoints
✅ Password hashing with bcrypt
✅ Comprehensive test suite with pytest
✅ API documentation at /docs
✅ Environment-based configuration
✅ Database integration ready (SQLAlchemy)

🔧 [execution] Running initial tests...

✅ **All tests passing!** (8/8)

Your FastAPI project is ready! To get started:
```bash
cd fastapi-project
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs for API documentation.
```

## 🧠 Learning and Adaptation

### Remembering User Preferences
```bash
💬 You: I prefer using spaces instead of tabs for Python code

🤖 Agent: I've noted your preference for spaces over tabs in Python code. I'll remember this for future code formatting and suggestions.

**Preference Saved:**
- Language: Python
- Indentation: Spaces (not tabs)
- Applied to: Code formatting, linting suggestions, new file creation

This preference will be applied automatically in future interactions. You can always change this by letting me know your updated preferences.
```

### Pattern Recognition
```bash
💬 You: Create a new API endpoint for user profiles

🤖 Agent: Based on your previous work, I notice you typically:
- Use FastAPI with SQLAlchemy models
- Include comprehensive error handling
- Add both unit and integration tests
- Follow RESTful conventions
- Use JWT authentication

I'll create the user profiles endpoint following these patterns...

🔧 [filesystem] Creating profile router...
🔧 [filesystem] Adding profile model...
🔧 [filesystem] Creating profile tests...

**Created endpoint following your established patterns:**
- GET /api/profiles/{user_id} - Get user profile
- PUT /api/profiles/{user_id} - Update user profile
- Includes JWT authentication requirement
- Comprehensive error handling for 404, 403, 422
- Full test coverage (6 new tests)
- Follows your preferred code style (spaces, descriptive names)

The implementation matches the patterns from your user authentication endpoints. All tests are passing!
```

## 🔧 Complex Workflows

### Bug Investigation and Fix
```bash
💬 You: Users are reporting login failures, but I can't reproduce the issue

🤖 Agent: I'll help investigate the login failures. Let me gather information systematically.

🔧 [filesystem] Reading application logs...
🔧 [git] Checking recent changes to auth code...
🔧 [execution] Running test suite...
🔧 [code_analysis] Analyzing auth module...

**Investigation Results:**

**📊 Log Analysis:**
- 47 failed login attempts in last 24 hours
- Pattern: All failures have "Invalid token format" error
- Affected timeframe: Started 2 days ago at 14:30 UTC

**🔍 Code Analysis:**
- Recent commit changed JWT secret rotation
- New environment variable JWT_SECRET_KEY not set in production
- Fallback to default secret causing token validation failures

**🧪 Test Results:**
- All tests pass in development (using test secrets)
- Issue likely environment-specific

**🔧 Root Cause Found:**
Production environment missing JWT_SECRET_KEY variable after recent deployment.

**Suggested Fix:**
1. Set JWT_SECRET_KEY in production environment
2. Add environment variable validation on startup
3. Add monitoring for JWT token failures

Would you like me to:
1. Create a hotfix for the missing environment variable?
2. Add startup validation to prevent this in the future?
3. Set up monitoring alerts for auth failures?
```

### Code Refactoring
```bash
💬 You: The auth module is getting too complex. Help me refactor it

🤖 Agent: I'll analyze the auth module and propose a refactoring plan.

🔧 [code_analysis] Analyzing auth module complexity...
🔧 [code_analysis] Checking dependencies...
🔧 [filesystem] Reading auth-related files...

**Complexity Analysis:**
- **auth.py**: 342 lines (recommended: <200)
- **Cyclomatic complexity**: 15 (recommended: <10)
- **Functions**: 12 (some doing multiple responsibilities)
- **Dependencies**: Mixed concerns (validation, DB, JWT, email)

**Refactoring Plan:**

**Phase 1: Extract Services**
- `services/jwt_service.py` - Token generation/validation
- `services/email_service.py` - Email notifications  
- `services/user_service.py` - User operations

**Phase 2: Separate Validation**
- `validators/auth_validators.py` - Input validation
- `schemas/auth_schemas.py` - Pydantic models

**Phase 3: Extract Utilities**
- `utils/password_utils.py` - Password hashing/verification
- `utils/token_utils.py` - Token utilities

**Benefits:**
✅ Single Responsibility Principle
✅ Easier testing (smaller units)
✅ Better reusability
✅ Clearer dependencies

Shall I proceed with this refactoring? I'll ensure all tests continue to pass throughout the process.
```

## 🎯 Advanced Features

### Multi-step Workflow
```bash
💬 You: Help me prepare this feature branch for production

🤖 Agent: I'll help you prepare your feature branch for production deployment. Let me run through the complete checklist.

**🔍 Pre-Production Checklist:**

🔧 [git] Checking branch status...
🔧 [code_analysis] Running security scan...
🔧 [execution] Running full test suite...
🔧 [code_analysis] Checking code quality...
🔧 [git] Analyzing commit history...

**Results:**

**✅ Git Status**
- Branch: feature/user-notifications
- 23 commits ahead of main
- No merge conflicts with main
- All commits have descriptive messages

**⚠️ Security Scan**
- 1 medium-risk issue: API keys in test files
- Recommendation: Move to environment variables

**✅ Test Coverage**
- Unit tests: 94% coverage
- Integration tests: All passing
- Performance tests: Within acceptable limits

**⚠️ Code Quality**
- 2 functions exceed complexity threshold
- Documentation coverage: 87% (target: 90%)

**Production Readiness Actions:**

🔧 [filesystem] Moving API keys to environment variables...
🔧 [code_analysis] Refactoring complex functions...
🔧 [filesystem] Adding missing documentation...
🔧 [git] Creating production-ready commit...

**✅ All Issues Resolved!**

Your feature branch is now production-ready:
- Security issues fixed
- Code complexity reduced
- Documentation completed
- Clean commit history

Ready to merge to main? I can also help with:
1. Creating the merge request
2. Setting up deployment pipeline
3. Planning rollback strategy
```

This demonstrates the AI Coding Agent's ability to handle complex, multi-step development workflows while maintaining safety, learning user preferences, and providing comprehensive assistance throughout the development lifecycle.