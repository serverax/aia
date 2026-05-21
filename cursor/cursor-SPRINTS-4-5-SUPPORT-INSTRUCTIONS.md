╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                     SYNTHETIC ENTERPRISE - CURSOR TEAM                        ║
║                      Sprints 4, 5 & On-Call Support                          ║
║                                                                               ║
║              Frontend Development & UI/UX (Weeks 8-28)                       ║
║                                                                               ║
║   Team: Cursor (1 Frontend Engineer)                                         ║
║   Duration: 20 weeks                                                         ║
║   Current: Sprints 4-5 (active)                                              ║
║   Future: On-call support Sprints 9-12                                       ║
║   Total Story Points: 12 (core) + support tasks                              ║
║   Budget: $100,000                                                           ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════════════════

SAVE LOCATION FOR THIS FILE:

📁 F:\aia\cursor\SPRINTS-4-5-SUPPORT-INSTRUCTIONS.md
OR
📁 /mnt/f/aia/cursor/SPRINTS-4-5-SUPPORT-INSTRUCTIONS.md

═══════════════════════════════════════════════════════════════════════════════

TEAM OVERVIEW

Cursor Team Responsibilities:
├─ Sprint 4: Frontend application & interactive UI
├─ Sprint 5: Document editor agent (DOCX/PDF integration)
├─ Weeks 15-28: On-call support for advanced features
│   ├─ New UI components for knowledge graph
│   ├─ Visualization dashboard updates
│   ├─ Confidence display updates
│   ├─ Proof verification widgets
│   └─ Mobile responsiveness
└─ Defense sector UI readiness

Team Members:
├─ Primary: 1 Senior Frontend Engineer (React/TypeScript)
└─ Support: Share with Cursor for mobile/responsive

Communication:
├─ Daily standups: 9:00 AM UTC
├─ Weekly reviews: Friday 3:00 PM UTC
├─ Slack channel: #cursor-frontend
├─ Github: serverax/aia (feature branches)
└─ UI design reviews: Async Figma

═══════════════════════════════════════════════════════════════════════════════

## CURRENT WORK: SPRINTS 4 & 5 (WEEKS 8-11)

[See existing documentation: cursor/SPRINT-4-5-INSTRUCTIONS.md]

Your current deliverables are on track. Continue with:

### SPRINT 4: FRONTEND APPLICATION (Weeks 8-9)

**Status:** ✅ IN PROGRESS (Week 8-9)
**Story Points:** 7
**Budget:** $35,000

**Your Deliverables:**
```
✅ frontend/components/Dashboard.tsx
✅ frontend/components/DocumentUpload.tsx
✅ frontend/components/AnalysisResults.tsx
✅ frontend/components/ComplianceOfficer.tsx
✅ frontend/styles/ (Tailwind CSS)
✅ tests/frontend/ (unit + integration)
✅ cursor/SPRINT-4-COMPLETION-REPORT.md
```

**Week 9 Deadline:**
- [ ] All components passing tests
- [ ] Mobile responsive (verified)
- [ ] Accessibility (WCAG 2.1 AA)
- [ ] Performance (< 3s load)
- [ ] Team sign-off

### SPRINT 5: EDITOR AGENT (Weeks 10-11)

**Status:** ⏳ READY (awaiting after Sprint 4)
**Story Points:** 5
**Budget:** $25,000

**Your Deliverables:**
```
├─ frontend/components/DocumentEditor.tsx
├─ services/editor_agent/main.py (integration)
├─ tests/editor/ (unit + integration)
└─ cursor/SPRINT-5-COMPLETION-REPORT.md
```

**Week 11 Deadline:**
- [ ] DOCX editing working
- [ ] PDF annotation working
- [ ] Word export functionality
- [ ] Performance acceptable
- [ ] Team sign-off

---

## PHASE 2: ON-CALL SUPPORT (WEEKS 15-28)

After Sprint 5 completes (Week 11), you transition to **ON-CALL** status.

**On-Call Responsibilities:**

```
Weeks 15-18 (Sprint 9 - minimal):
  ├─ Status: STANDBY
  ├─ Allocation: 10% (react to urgent UI needs)
  ├─ Priority: Low (Claude Code on critical path)
  └─ Role: Available if UI issues arise

Weeks 19-21 (Sprint 10 - minor):
  ├─ Status: STANDBY
  ├─ Allocation: 15% (Graph viz prep)
  ├─ Task: Prepare graph visualization component
  └─ Role: Review Graph Team's visualization design

Weeks 22-24 (Sprint 11 - moderate):
  ├─ Status: ACTIVE SUPPORT
  ├─ Allocation: 30% (Graph viz development)
  ├─ Task: Build interactive graph visualization
  └─ Role: Implement Graph Team's designs

Weeks 25-28 (Sprint 12 - active):
  ├─ Status: ACTIVE SUPPORT
  ├─ Allocation: 40% (UI integration)
  ├─ Task: Final UI polish & integration
  └─ Role: Ensure all new features are UI-ready

TOTAL SUPPORT: 12 weeks, 20-25% average allocation
```

---

## SUPPORT TASKS (WEEKS 15-28)

### TASK S-10: GRAPH VISUALIZATION PREP (Weeks 19-21)

**Assigned to:** Cursor Frontend Engineer (15% time)
**Points:** 2
**Timeline:** Weeks 19-21

**Deliverables:**
```
├─ File: frontend/components/GraphVisualizer.tsx (skeleton)
├─ File: frontend/components/GraphControls.tsx
├─ File: frontend/styles/graph_visualization.css
├─ File: cursor/sprint-10/graph-viz-prep-notes.md
└─ File: GRAPH-VIZ-REQUIREMENTS.md
```

**What to Build:**
```
1. Review Graph Team's design requirements
2. Prepare React component structure
3. Setup D3.js integration
4. Create placeholder visualization
5. Define component interfaces
6. Prepare for Graph Team handoff

Components Needed:
├─ GraphVisualizer.tsx: Main component
├─ GraphControls.tsx: Search, filter, zoom
├─ GraphNode.tsx: Individual node rendering
├─ GraphEdge.tsx: Relationship rendering
├─ GraphLegend.tsx: Entity type legend
└─ GraphExport.tsx: Export options (PNG, JSON)
```

---

### TASK S-11: GRAPH VISUALIZATION BUILD (Weeks 22-24)

**Assigned to:** Cursor Frontend Engineer (30% time)
**Points:** 4
**Timeline:** Weeks 22-24

**Deliverables:**
```
├─ File: frontend/components/GraphVisualizer.tsx (complete)
├─ File: frontend/components/neo4j_client.ts
├─ File: frontend/components/graph_layout.ts (D3)
├─ File: tests/frontend/test_graph_viz.tsx
├─ File: frontend/styles/graph_visualization.css
├─ File: cursor/sprint-11/graph-viz-implementation.md
└─ File: GRAPH-VIZ-DESIGN-SYSTEM.md
```

**What to Build:**
```
1. Interactive force-directed graph (D3)
2. Entity type color-coding
3. Relationship strength (edge thickness)
4. Click drill-down for entity details
5. Search & filter functionality
6. Pan, zoom, drag interactions
7. Path highlighting (causal chains)
8. Export as PNG/JSON
9. Responsive design (desktop & mobile)
10. Real-time updates from Neo4j

REQUIREMENTS:
├─ Render 100k+ nodes smoothly
├─ Interactions responsive (< 200ms)
├─ Mobile-friendly
├─ Accessibility (WCAG 2.1 AA)
├─ Performance optimized
└─ Works in all modern browsers

TESTING:
├─ Unit test: Component rendering
├─ Performance test: 100k nodes
├─ Interaction test: Click, drag, zoom
├─ Responsive test: Desktop/tablet/mobile
└─ Integration test: Real graph data
```

---

### TASK S-12A: CONFIDENCE DISPLAY (Weeks 25-26)

**Assigned to:** Cursor Frontend Engineer (20% time)
**Points:** 2
**Timeline:** Weeks 25-26

**Deliverables:**
```
├─ File: frontend/components/ConfidenceDisplay.tsx
├─ File: frontend/components/ConfidenceBadge.tsx
├─ File: frontend/styles/confidence_styling.css
├─ File: tests/frontend/test_confidence_display.tsx
└─ File: cursor/sprint-12/confidence-ui-notes.md
```

**What to Build:**
```
1. Confidence score visualization
2. Color-coded badges (high/medium/low)
3. Confidence explanation tooltip
4. Escalation flag (< 0.7 confidence)
5. User guidance text

DISPLAY OPTIONS:
├─ Numeric: "Confidence: 87%"
├─ Visual: Green/Yellow/Red badge
├─ Text: "High confidence - safe to rely on"
├─ Detailed: Breakdown of factors
└─ Escalation: "Review required" for < 0.7

ACCESSIBILITY:
├─ Color not only indicator
├─ ARIA labels for screen readers
├─ Keyboard navigation
└─ Mobile-friendly
```

---

### TASK S-12B: PROOF VERIFICATION WIDGET (Weeks 26-27)

**Assigned to:** Cursor Frontend Engineer (20% time)
**Points:** 2
**Timeline:** Weeks 26-27

**Deliverables:**
```
├─ File: frontend/components/CitationVerifier.tsx
├─ File: frontend/components/ProofViewer.tsx
├─ File: frontend/styles/proof_verification.css
├─ File: tests/frontend/test_proof_verifier.tsx
└─ File: cursor/sprint-12/proof-verification-ui.md
```

**What to Build:**
```
1. Citation verification widget
2. Proof chain visualization
3. "Verify Proof" button
4. Badge: "Verified" or "Tampered"
5. Proof details modal
6. Merkle path visualization

WORKFLOW:
├─ Click citation in results
├─ See "Verify" button
├─ Click to verify
├─ Shows: Hash, Signature, Timestamp
├─ Shows: Merkle path visually
├─ Result: ✅ Verified or ❌ Tampered

STYLING:
├─ Success (green): Verified
├─ Warning (orange): Unverified
├─ Error (red): Tampered
└─ Info (blue): Details
```

---

### TASK S-12C: ADVERSARIAL ALERTS (Week 27-28)

**Assigned to:** Cursor Frontend Engineer (20% time)
**Points:** 1
**Timeline:** Weeks 27-28

**Deliverables:**
```
├─ File: frontend/components/AdversarialAlert.tsx
├─ File: frontend/styles/alert_styling.css
├─ File: tests/frontend/test_alerts.tsx
└─ File: cursor/sprint-12/alerts-ui-notes.md
```

**What to Build:**
```
1. Alert banner when adversarial attack detected
2. Clear, non-technical messaging
3. Action buttons: "Learn more", "Report"
4. Dismissible but persistent in logs

ALERT TYPES:
├─ Injection attempt: "Suspicious input detected"
├─ Document tampering: "Document integrity issue"
├─ Encoding attack: "Unusual data format"
└─ Pattern match: "Security concern flagged"

STYLING:
├─ Prominent but not alarming
├─ Red banner with icon
├─ Clear action buttons
├─ Don't block user workflow
└─ Log for audit trail
```

---

### TASK S-12D: UI POLISH & TESTING (Week 28)

**Assigned to:** Cursor Frontend Engineer (30% time)
**Points:** 2
**Timeline:** Week 28

**Deliverables:**
```
├─ File: frontend/POLISH-CHECKLIST.md
├─ File: tests/frontend/test_full_ui.tsx
├─ File: tests/frontend/test_responsive.tsx
├─ File: tests/frontend/test_accessibility.tsx
├─ File: cursor/sprint-12/final-polish-notes.md
└─ File: cursor/PRODUCTION-UI-READINESS.md
```

**What to Do:**
```
Polish Checklist:
├─ Visual consistency across all pages
├─ Typography & spacing
├─ Color scheme validation
├─ Icon consistency
├─ Animation smoothness
├─ Loading states
├─ Error messages
├─ Success feedback
├─ Keyboard navigation
└─ Touch-friendly on mobile

Testing:
├─ Responsive design (all breakpoints)
├─ Accessibility (WCAG 2.1 AA)
├─ Performance (< 3s load)
├─ Browser compatibility
├─ Mobile browsers
├─ Offline functionality
├─ Print layout (if applicable)
└─ Dark mode (if applicable)

Final Checks:
├─ No console errors
├─ No broken links
├─ All images optimized
├─ Fonts loading correctly
├─ Analytics events firing
└─ Performance metrics acceptable
```

---

## SUPPORT WORKFLOW

**When Support Needed:**

```
1. Issue Reported
   └─ Graph Team / Gemini / Claude Code report UI need

2. Assessment
   └─ Cursor reviews requirement (24 hours)
   └─ Confirms feasibility

3. Implementation
   └─ If < 4 hours: Do immediately
   └─ If > 4 hours: Schedule in sprint

4. Testing
   └─ Cursor tests component
   └─ Requesting team validates

5. Deployment
   └─ Merge to staging
   └─ Verify in staging
   └─ Merge to production
```

**Support Request Template:**
```
Title: [SPRINT-X] UI Feature: [Component Name]

Description:
What is needed?
├─ Why?
├─ Which team needs it?
└─ Timeline required?

Requirements:
├─ Functional requirements
├─ Visual/UX requirements
├─ Performance targets
├─ Accessibility needs
└─ Browser support

Design:
├─ Figma link (if available)
├─ Example screenshot
├─ Layout description
└─ Interaction description

Timeline:
├─ When needed?
├─ Urgency level
└─ Blocking tasks?
```

---

## DEVELOPMENT ENVIRONMENT

**Frontend Stack:**
```
Framework: React 18+ (TypeScript)
Styling: Tailwind CSS
State: Zustand
API Client: Axios + React Query
Visualization: D3.js (graphs)
Testing: Jest + React Testing Library
Linting: ESLint + Prettier
Build: Webpack (with Vite prep)
```

**Directory Structure:**
```
F:\aia\
├── frontend/
│   ├── components/
│   │   ├── Dashboard.tsx (Sprint 4)
│   │   ├── DocumentUpload.tsx (Sprint 4)
│   │   ├── AnalysisResults.tsx (Sprint 4)
│   │   ├── ComplianceOfficer.tsx (Sprint 4)
│   │   ├── DocumentEditor.tsx (Sprint 5)
│   │   ├── GraphVisualizer.tsx (Sprint 11)
│   │   ├── ConfidenceDisplay.tsx (Sprint 12)
│   │   ├── CitationVerifier.tsx (Sprint 12)
│   │   ├── AdversarialAlert.tsx (Sprint 12)
│   │   └── (other components)
│   ├── styles/
│   │   ├── tailwind.css
│   │   ├── graph_visualization.css
│   │   ├── confidence_styling.css
│   │   ├── proof_verification.css
│   │   └── alert_styling.css
│   ├── hooks/
│   │   ├── useGraph.ts
│   │   ├── useConfidence.ts
│   │   └── (custom hooks)
│   ├── utils/
│   │   ├── api.ts (API client)
│   │   ├── graph_layout.ts (D3)
│   │   └── (utilities)
│   └── __tests__/
│       ├── test_*.tsx files
│       └── (test utilities)
└── cursor/
    ├── SPRINTS-4-5-SUPPORT-INSTRUCTIONS.md (this file)
    ├── sprint-4/
    │   ├── SPRINT-4-COMPLETION-REPORT.md
    │   └── design-notes.md
    ├── sprint-5/
    │   ├── SPRINT-5-COMPLETION-REPORT.md
    │   └── editor-notes.md
    └── sprint-12-support/
        ├── graph-viz-prep-notes.md
        ├── graph-viz-implementation.md
        ├── confidence-ui-notes.md
        ├── proof-verification-ui.md
        ├── alerts-ui-notes.md
        ├── final-polish-notes.md
        └── PRODUCTION-UI-READINESS.md
```

---

## COMMUNICATION

**Daily Standup (Async):**
- Time: 9:00 AM UTC
- Channel: #cursor-frontend
- Format: 3-bullet update

**Weekly Review:**
- Time: Friday 3:00 PM UTC
- Duration: 30 minutes
- Format: Video + demo

**Design Reviews:**
- Channel: Figma comments
- Async: 24-hour response time
- Reviewer: Design lead

**Blocking Issues:**
- Slack: Direct message to PM
- Escalation: Immediate call if needed

---

## TESTING REQUIREMENTS

**All UI Components Must Have:**
```
Unit Tests:
├─ Rendering test
├─ Props test
├─ State management
├─ Event handlers
└─ Accessibility

Integration Tests:
├─ Component interactions
├─ API integration
├─ Data flow
└─ Real-world scenarios

Performance Tests:
├─ Render time < 200ms
├─ Paint time < 500ms
├─ Memory leaks: None
└─ Bundle size acceptable

Accessibility Tests:
├─ WCAG 2.1 AA compliance
├─ Keyboard navigation
├─ Screen reader support
├─ Color contrast
└─ Focus management

Responsive Tests:
├─ Mobile (375px)
├─ Tablet (768px)
├─ Desktop (1024px+)
└─ Large screens (1440px+)
```

**Test Coverage Target: > 80%**

---

## BUDGET ALLOCATION

**Sprint 4 (Weeks 8-9):**
- 80 hours × $400/hr = $32,000

**Sprint 5 (Weeks 10-11):**
- 50 hours × $400/hr = $20,000

**Support (Weeks 15-28, 14 weeks × 20% average):**
- 70 hours × $400/hr = $28,000

**Contingency (10%):**
- $20,000

**Total Cursor Budget: $100,000**

---

## SUCCESS CRITERIA & SIGN-OFF

**Sprint 4 Sign-Off (End of Week 9):**
```
✅ All components complete
✅ All tests passing (> 80% coverage)
✅ Accessibility verified (WCAG 2.1 AA)
✅ Performance acceptable (< 3s load)
✅ Mobile responsive verified
✅ Code review approved
✅ Design review approved
✅ Team sign-off
```

**Sprint 5 Sign-Off (End of Week 11):**
```
✅ Editor fully functional
✅ DOCX integration working
✅ PDF annotation working
✅ Export functionality verified
✅ All tests passing
✅ Performance verified
✅ Team sign-off
```

**Support Phase Sign-Off (End of Week 28):**
```
✅ All support tasks completed
✅ Graph visualization polished
✅ Confidence display implemented
✅ Proof verification widget working
✅ Adversarial alerts functioning
✅ Full UI polish complete
✅ Accessibility verified
✅ Mobile responsiveness confirmed
✅ All tests passing
✅ Production ready
✅ Team sign-off
```

---

## KEY DATES

```
Week 8-9: Sprint 4 (active)
Week 10-11: Sprint 5 (active)
Week 12-14: Buffer/cleanup
Week 15-18: Sprint 9 support (standby, 10%)
Week 19-21: Sprint 10 support (prep, 15%)
Week 22-24: Sprint 11 support (active, 30%)
Week 25-28: Sprint 12 support (active, 40%)
Week 29: Production deployment (go-live)
```

---

## APPROVAL & SIGN-OFF

**This document approved by:**
- [ ] Cursor Frontend Lead
- [ ] Project Manager
- [ ] Design Lead
- [ ] QA Lead

**Date Approved:** _______________
**Sprint 4 Start:** Week 8 (2026-05-21)
**Go-Live Date:** Week 29 (2026-07-16)

---

**Ready to build the best UI for defense-grade AI! 🎨**

Questions? Ask in #cursor-frontend
