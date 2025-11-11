# Phase 3: Documentation Organization Plan

## Current State

### Root Directory (17 markdown files)
**Project Documentation:**
1. `README.md` - Main project documentation (KEEP in root)
2. `ARCHITECTURE.md` - Architecture overview
3. `CHANGELOG.md` - Version history (KEEP in root)
4. `CONFIGURATION.md` - Configuration guide
5. `CONTRIBUTING.md` - Contribution guidelines (KEEP in root)
6. `DEVELOPER_GUIDE.md` - Developer workflow
7. `KIRO_SETUP.md` - Kiro-specific setup
8. `SECURITY.md` - Security policy (KEEP in root)
9. `LICENSE` - License file (KEEP in root)

**Refactoring Documentation (8 files - TEMPORARY):**
1. `CLEANUP_STATUS.md`
2. `CODEBASE_ISSUES_REPORT.md`
3. `MODERNIZATION_COMPLETE.md`
4. `MODERNIZATION_SUMMARY.md`
5. `PHASE1_COMPLETE.md`
6. `PHASE2_COMPLETE.md`
7. `PHASE2_PLAN.md`
8. `REFACTORING_COMPLETE.md`
9. `REFACTORING_SUMMARY.md`

### docs/ Directory (8 files)
1. `README.md` - Docs index
2. `distribution.md` - Distribution guide
3. `enhanced_parsing_examples.md` - Parsing examples
4. `integration_testing.md` - Integration testing
5. `kiro-configuration.md` - Kiro config
6. `recent-fixes-and-enhancements.md` - Recent changes
7. `test-maintenance-procedures.md` - Test maintenance
8. `testing-with-poetry.md` - Poetry testing

## Problems

1. **Too many files in root** - 17 markdown files cluttering root directory
2. **Duplicate topics** - KIRO_SETUP.md and docs/kiro-configuration.md
3. **Refactoring docs in root** - Temporary documentation mixed with permanent
4. **No clear organization** - Hard to find specific documentation
5. **Inconsistent naming** - Some use hyphens, some use underscores

## Strategy

### Keep in Root (5 files)
Essential files that should remain in root:
1. `README.md` - Main entry point
2. `CHANGELOG.md` - Version history
3. `CONTRIBUTING.md` - How to contribute
4. `LICENSE` - License file
5. `SECURITY.md` - Security policy

### Move to docs/ (4 files)
Project documentation:
1. `ARCHITECTURE.md` → `docs/architecture.md`
2. `CONFIGURATION.md` → `docs/configuration.md`
3. `DEVELOPER_GUIDE.md` → `docs/developer-guide.md`
4. `KIRO_SETUP.md` → Merge with `docs/kiro-configuration.md`

### Move to docs/refactoring/ (8 files)
Refactoring documentation (historical record):
1. `CLEANUP_STATUS.md` → `docs/refactoring/cleanup-status.md`
2. `CODEBASE_ISSUES_REPORT.md` → `docs/refactoring/issues-report.md`
3. `MODERNIZATION_COMPLETE.md` → `docs/refactoring/modernization-complete.md`
4. `MODERNIZATION_SUMMARY.md` → `docs/refactoring/modernization-summary.md`
5. `PHASE1_COMPLETE.md` → `docs/refactoring/phase1-complete.md`
6. `PHASE2_COMPLETE.md` → `docs/refactoring/phase2-complete.md`
7. `PHASE2_PLAN.md` → `docs/refactoring/phase2-plan.md`
8. `REFACTORING_COMPLETE.md` → `docs/refactoring/complete.md`
9. `REFACTORING_SUMMARY.md` → `docs/refactoring/summary.md`

### Reorganize docs/ Directory
Create clear structure:
```
docs/
├── index.md (new - main docs entry point)
├── architecture.md (moved from root)
├── configuration.md (moved from root)
├── developer-guide.md (moved from root)
├── kiro-setup.md (merged KIRO_SETUP.md + kiro-configuration.md)
├── distribution.md (existing)
├── integration-testing.md (renamed)
├── testing-with-poetry.md (existing)
├── test-maintenance.md (renamed)
├── parsing-examples.md (renamed)
├── recent-changes.md (renamed)
└── refactoring/ (new directory)
    ├── README.md (new - refactoring index)
    ├── complete.md
    ├── summary.md
    ├── issues-report.md
    ├── phase1-complete.md
    ├── phase2-complete.md
    ├── phase2-plan.md
    ├── modernization-summary.md
    ├── modernization-complete.md
    └── cleanup-status.md
```

## Implementation Steps

### Step 1: Create docs/refactoring/ directory
```bash
mkdir -p docs/refactoring
```

### Step 2: Move refactoring docs
```bash
mv CLEANUP_STATUS.md docs/refactoring/cleanup-status.md
mv CODEBASE_ISSUES_REPORT.md docs/refactoring/issues-report.md
mv MODERNIZATION_COMPLETE.md docs/refactoring/modernization-complete.md
mv MODERNIZATION_SUMMARY.md docs/refactoring/modernization-summary.md
mv PHASE1_COMPLETE.md docs/refactoring/phase1-complete.md
mv PHASE2_COMPLETE.md docs/refactoring/phase2-complete.md
mv PHASE2_PLAN.md docs/refactoring/phase2-plan.md
mv REFACTORING_COMPLETE.md docs/refactoring/complete.md
mv REFACTORING_SUMMARY.md docs/refactoring/summary.md
```

### Step 3: Move project docs
```bash
mv ARCHITECTURE.md docs/architecture.md
mv CONFIGURATION.md docs/configuration.md
mv DEVELOPER_GUIDE.md docs/developer-guide.md
```

### Step 4: Merge and rename docs
```bash
# Merge KIRO_SETUP.md with docs/kiro-configuration.md
# Rename for consistency
mv docs/integration_testing.md docs/integration-testing.md
mv docs/test-maintenance-procedures.md docs/test-maintenance.md
mv docs/enhanced_parsing_examples.md docs/parsing-examples.md
mv docs/recent-fixes-and-enhancements.md docs/recent-changes.md
mv docs/testing-with-poetry.md docs/testing-with-poetry.md
```

### Step 5: Create index files
- Create `docs/index.md` - Main documentation index
- Create `docs/refactoring/README.md` - Refactoring documentation index

### Step 6: Update references
- Update README.md links
- Update CONTRIBUTING.md links
- Update any other files referencing moved docs

## Benefits

### 1. Cleaner Root Directory
- **Before**: 17 markdown files
- **After**: 5 essential files
- **Reduction**: 70% fewer files in root

### 2. Better Organization
- Clear separation of concerns
- Easy to find documentation
- Logical grouping

### 3. Consistent Naming
- All docs use hyphens (kebab-case)
- Clear, descriptive names
- No abbreviations

### 4. Historical Record
- Refactoring docs preserved in `docs/refactoring/`
- Easy to reference later
- Not cluttering main docs

### 5. Easier Navigation
- `docs/index.md` as entry point
- Clear categories
- Better discoverability

## Comparison with EXAMPLE_ShokoBot

### EXAMPLE_ShokoBot Structure
```
EXAMPLE_ShokoBot/
├── README.md
├── SETUP_GUIDE.md
├── QUICK_REFERENCE.md
├── LICENSE
└── docs/
    ├── README.md
    ├── MODULAR_CLI_ARCHITECTURE.md
    ├── APPCONTEXT_USAGE.md
    └── ASYNC_OPPORTUNITIES_ANALYSIS.md
```

### Our Target Structure
```
mcp-server-anime/
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── SECURITY.md
└── docs/
    ├── index.md
    ├── architecture.md
    ├── configuration.md
    ├── developer-guide.md
    ├── kiro-setup.md
    ├── ... (other docs)
    └── refactoring/
        └── ... (historical docs)
```

**Alignment**: ✅ Similar clean root, organized docs/

## Success Criteria

- [ ] Root directory has only 5 markdown files
- [ ] All project docs in docs/ directory
- [ ] Refactoring docs in docs/refactoring/
- [ ] Consistent naming (kebab-case)
- [ ] docs/index.md created
- [ ] docs/refactoring/README.md created
- [ ] All references updated
- [ ] No broken links

## Expected Outcome

### Root Directory
```
mcp-server-anime/
├── README.md              # Main entry point
├── CHANGELOG.md           # Version history
├── CONTRIBUTING.md        # How to contribute
├── LICENSE                # License
├── SECURITY.md            # Security policy
├── pyproject.toml
├── Makefile
├── .gitignore
└── ... (code directories)
```

### Documentation Directory
```
docs/
├── index.md               # Documentation hub
├── architecture.md        # System architecture
├── configuration.md       # Configuration guide
├── developer-guide.md     # Developer workflow
├── kiro-setup.md         # Kiro integration
├── distribution.md        # Distribution guide
├── integration-testing.md # Integration tests
├── testing-with-poetry.md # Poetry testing
├── test-maintenance.md    # Test maintenance
├── parsing-examples.md    # Parsing examples
├── recent-changes.md      # Recent updates
└── refactoring/          # Historical refactoring docs
    ├── README.md
    ├── complete.md
    ├── summary.md
    └── ... (9 files total)
```

## Timeline

- **Step 1-2**: 5 minutes (create directory, move refactoring docs)
- **Step 3-4**: 5 minutes (move and rename project docs)
- **Step 5**: 10 minutes (create index files)
- **Step 6**: 10 minutes (update references)
- **Total**: ~30 minutes

## Next Steps After Phase 3

### Phase 4: Code Organization
- Mark deprecated code
- Document active implementations
- Remove unused code
- Add architecture decision records
