# Contributing to AegisAIS

We welcome contributions! Please follow these guidelines to ensure code quality and consistency.

## Development Workflow

1. **Branch from `main`** using conventional branch names:
   - `feat/short-description` for new features
   - `fix/short-description` for bug fixes
   - `docs/short-description` for documentation
   - `refactor/short-description` for refactoring

2. **Use conventional commit messages**:

   ```
   feat: add new detection rule for speed anomalies
   fix: resolve WebSocket connection timeout
   docs: update API documentation
   refactor: simplify alert filtering logic
   ```

3. **Add tests** for any new detection rules or API endpoints:

   ```bash
   cd apps/api
   pytest tests/ -v
   ```

4. **Ensure code quality**:

   ```bash
   # Frontend linting
   cd apps/web
   npm run lint

   # Backend type checking
   cd apps/api
   mypy app/
   ```

5. **Update documentation** in `docs/` for any public-facing changes

6. **Open a pull request** using the [PR template](./.github/PULL_REQUEST_TEMPLATE.md)

## Code Standards

### Python (Backend)

- Use type hints for all function signatures
- Follow [PEP 8](https://pep8.org/) style guidelines
- Write docstrings for modules, classes, and public methods
- Minimum Python 3.11

### TypeScript (Frontend)

- Enable strict mode (`strict: true` in tsconfig.json)
- Write tests for new components and utilities
- Use descriptive variable names (no single-letter vars except loop counters)
- Prefer functional components with hooks

### Commit Structure

- One logical change per commit
- Keep commits focused and atomic
- Include context in commit messages (the "why", not just the "what")

## Testing

- **Backend**: `cd apps/api && pytest tests/ -v`
- **Frontend**: `cd apps/web && npm run test` (if configured)

## Pull Request Process

1. Ensure all tests pass
2. Keep PRs focused—one feature or fix per PR
3. Write clear PR descriptions
4. Respond to code review feedback promptly
5. Request re-review after changes

## Reporting Issues

- Use GitHub Issues with clear, descriptive titles
- Include steps to reproduce for bugs
- Attach relevant logs or screenshots
- Label appropriately (bug, enhancement, documentation)

## Questions or Need Help?

- Check existing documentation in `docs/`
- Review the [Architecture guide](./docs/architecture/ARCHITECTURE.md) for system design
- Open a discussion in GitHub Issues

Thanks for contributing! 🙌
