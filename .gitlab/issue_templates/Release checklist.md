## Release Checklist: vX.Y.Z

This checklist tracks the process for releasing version **vX.Y.Z** of the OpenFlexure Microscope Server.

---

### Phase 1: Preparation (T-6 Weeks _minimum_)

This phase focuses on planning the release and, crucially, getting any major infrastructure or build system changes merged *before* the feature freeze.

* [ ] **Prepare: **Create the `Server vX.Y.Z`/`Server vX.Y.Z-(alpha|beta)A` milestone in GitLab at organisation level, and create an issue with this template.
* [ ] **Define Scope:**  Tag all intended Issues and feature MRs with it. This is often done in a planning meeting with the core team. Issues and MRs should be tagged in:
    * [ ] Server repo
    * [ ] Stitching repo
    * [ ] OS customiser repo
    * [ ] OFM CLI tools
* [ ] **Define upstream versions:** Does this release depend on a major dependency change (such as new LabThings version)? If so these must have issues.
* [ ] **Schedule:** Set and announce the **Feature Freeze** and **Release Date**. Feature freeze should be at least 2 weeks before the release date.
* [ ] **Build System:** **Deadline:** All build system MRs must be merged and tested. (This should happen *as early as possible* in the cycle).

---

### Phase 2: Feature Freeze (T-2 Weeks)

* [ ] **Announce:** Announce the Feature Freeze deadline one week out. This should be announced on the OpenFlexure Forum and in a message/email to the core team.
* [ ] **Deadline:** **FEATURE FREEZE**. All MRs for the milestone must be merged.
* [ ] **Branch:** Create a `release/vX.Y.Z` branch from `main`.
    * *From this point, only bug fixes (regressions) are merged into this branch.*
* [ ] **Communication:** Inform the team that all new feature work should target the *next* milestone.

---

### Phase 3: Testing & Qualification (T-1 Week)

This phase is dedicated to intensive testing and bug fixing on the `release/vX.Y.Z` branch.

* [ ] **Create Image:** Flash at least one SD card with the new image.
* [ ] **Create Test Plan:** Document the specific tests to be run.
* [ ] **Execute Test Plan:**
    * [ ] Camera Calibration
        * [ ] Picamera v2
        * [ ] Picamera HQ
    * [ ] Camera Stage Mapping
        * [ ] v7 Microscope
        * [ ] Simulation
    * [ ] Movement
        * [ ] v7 Microscope
        * [ ] Simulation
    * [ ] Autofocus
        * [ ] v7 Microscope
        * [ ] Simulation
    * [ ] Smart Scan + stitching
        * [ ] v7 Microscope (we probably need a bit of detail here RE slides)
        * [ ] Simulation
    * [ ] Recentre and ROM (v7 Microscope only)
    * [ ] Opening each tab and sub-tab and checking things look as expected
        * [ ] v7 Microscope 
        * [ ] Simulation
        * [ ] Manual
* [ ] **Triage:** Triage all bugs found. Fix any release-blocking bugs.
* [ ] **Repeat:** Re-build image and re-test as bugs are fixed. Update release date if absolutely necessary. (Optional)

---

### Phase 4: Release Day (T-0)

* [ ] **Final Version Bump:**
    * [ ] **Server Package:** Update version number (add specific files).
    * [ ] **Stitching Package:** Update version number (add specific files).
    * [ ] Commit and merge the final version bumps into the `release/vX.Y.Z` branch.
* [ ] **Final Build:** Generate the final, official release image from the `release/vX.Y.Z` branch.
* [ ] **Draft Notes:** Draft the release notes and forum post.
* [ ] **Merge:** Merge the `release/vX.Y.Z` branch into `main`.
* [ ] **Tag:** Create a new Git tag on `main` (e.g., `vX.Y.Z`).
* [ ] **Publish:**
    * [ ] Push the tag to GitLab.
    * [ ] Publish new versions of software sub-packages, such as openflexure-stitching, on PyPi.
    * [ ] Create a new **GitLab Release** from the tag.
    * [ ] Upload the final release image and other artifacts to the GitLab Release.
    * [ ] Paste the release notes into the GitLab Release description.

---

### Phase 5: Post-Release

* [ ] **Communicate:** Publish the release announcement on the OpenFlexure forum.
* [ ] **Announce:** Share the forum post on other relevant channels (e.g., LinkedIn, Emailing Collaborators).
* [ ] **Close:** Close this issue and the corresponding GitLab Milestone.
* [ ] **Celebrate!**
