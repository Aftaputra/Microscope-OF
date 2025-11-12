## Release Checklist: vX.Y.Z

This checklist tracks the process for releasing version **vX.Y.Z** of the OpenFlexure Microscope Server.

---

### Branching Strategy (as of v3 development)

The current branching strategy is for **alpha and beta development of v3**.
There is an issue open (#606) to discuss branching beyond v3.

* The **default branch** is called `v3`.
* **Feature branches** are made from `v3` and merged back into `v3`.
* We **do not** make a new release branch.
* We **still perform a feature freeze** before release.
* We **still tag each release** and post it on the forum.
* We **do not rename** the `v3` branch or create additional long-lived branches for releases.

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

### Phase 2: Feature Freeze And Upstream Releases (T-2 Weeks)

* [ ] **Announce:** Announce the Feature Freeze deadline one week out. This should be announced on the OpenFlexure Forum and in a message/email to the core team.
* [ ] **Deadline:** **FEATURE FREEZE**. All MRs for the milestone must be merged.
* [ ] **Deadline:** **UPSTREAM RELEASES**. Any of our repos/packages upstream of the OS and server should have a defined release, for this release to target.
    * [ ] Stitching Released
* [ ] **Branching Note:**  During alpha and beta development, feature freeze marks the point where only **bug fixes and release preparation** may be merged into the default branch.
* [ ] **Communication:** Inform the team that all new feature work should target the *next* milestone.

---

### Phase 3: Testing & Qualification (T-1 Week)

This phase is dedicated to intensive testing and bug fixing.

* [ ] **Create Image:** Flash at least one SD card with the new image. This image should be created off the default branch.
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
        * [ ] v7 Microscope
            * [ ] At least 2 different H&E stained slides
            * [ ] A blue stained biology slide, such as a wheat stem
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

By this stage:

* All upstream packages are released.
* We will release the exact image used for testing.

* [ ] **Draft Notes:** Draft the release notes for:
    * [ ] High level summary for the sever release notes/changelog
    * [ ] High level summary for the OS release notes
    * [ ] Combined summary for the forum
* [ ] **Final Server Repo Commit:**
    * [ ] Update version string in:
        * [ ] `pyproject.toml`
        * [ ] `test_version_strings.py`
        * [ ] `package.json`
        * [ ] `package-lock.json` (in 2 places!)
    * [ ] Create `CHANGELOG` entry
        * [ ] Add a title that is a link to the GitLab compare between the last release tag and this soon-to-be-made tag.
        * [ ] Add the a high level summary of the server changes
        * [ ] Run changelog helper to generate the list of MRs since the last tag `python change_log_helper.py -b v3 <LAST-TAG-NAME>` and copy these in below the summary.
        * [ ] Run `codespell` on the changelog and use `<!-- codespell:ignore XYZ -->` to silence codespell on any spelling errors in MR titles.
    * [ ] Commit, Push, and Merge
* [ ]  **Release:**
    * [ ] On `build.openflexure.org` copy the image that passed testing from `/raspbian-openflexure/testing/` to `/raspbian-openflexure/v3_pre_release/`.
    * [ ] **OS RELEASE**
        * [ ] Go to the OS Customiser *Releases* page on GitLab and select New Release
        * [ ] Create a new Tag Name in the format `vX.Y.Z` or `vX.Y.Z-(alpha|beta)A`
        * [ ] **Important!** Enter a simple description into the `create tag` dialog, or GitLab only creates a lightweight tag. `Release for vX.Y.Z-(alpha|beta)A` is minimal and can be used. Check it is targeted at the correct branch, and save the tag.
        * [ ] Copy in the High level summary for the OS into release notes
        * [ ] Enter the URL to the OS image into the box at the bottom. with "Link Title" as `SD Card Image`.
        * [ ] Create the release (This will create the tag)
    * [ ] **SERVER RELEASE**
        * [ ] Go to the Sever *Releases* page on GitLab and select New Release
        * [ ] Create a new Tag Name in the format `vX.Y.Z` or `vX.Y.Z-(alpha|beta)A`
        * [ ] **Important!** Enter a simple description into the `create tag` dialog, or GitLab only creates a lightweight tag. `Release for vX.Y.Z-(alpha|beta)A` is minimal and can be used. Check it is targeted at the correct branch, and save the tag.
        * [ ] Copy in the relevant section from the `CHANGELOG`
        * [ ] Enter the URL to the OS image into the box at the bottom. with "Link Title" as `SD Card Image`.
        * [ ] Create the release (This will create the tag)

---

### Phase 5: Post-Release

* [ ] **Communicate:** Publish the release announcement on the OpenFlexure forum.
* [ ] **Announce:** Share the forum post on other relevant channels (e.g., LinkedIn, Emailing Collaborators).
* [ ] **Close:** Close this issue and the corresponding GitLab Milestone.
* [ ] **Celebrate!**
