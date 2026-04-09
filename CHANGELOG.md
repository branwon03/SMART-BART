# CHANGELOG

<!-- version list -->

## v0.11.1 (2026-04-09)

### Bug Fixes

- Merge conflict lint errors
  ([`8246a78`](https://github.com/cse120-ucm/S26-CSE-312/commit/8246a7856aedee4ecb1fb323f602d11f9e53e89c))


## v0.11.0 (2026-04-09)

### Bug Fixes

- Lint + mypy build errors
  ([`0e8e3d8`](https://github.com/cse120-ucm/S26-CSE-312/commit/0e8e3d89889f0296d208cdc309c8f95d609196cf))

### Chores

- Update ignore files
  ([`d84f851`](https://github.com/cse120-ucm/S26-CSE-312/commit/d84f851a24c0e991af558ccd821e27c4c7767085))

### Features

- Adding issue editing e2e + status column
  ([`c987dd5`](https://github.com/cse120-ucm/S26-CSE-312/commit/c987dd55d1610174ecfb2f4d9d7fff475205b030))


## v0.10.2 (2026-04-09)

### Bug Fixes

- Prompt now handles wrong scanner priority, and wrong GROUNDS classifications
  ([`ce51f08`](https://github.com/cse120-ucm/S26-CSE-312/commit/ce51f08a5beae8fe405a67c19e6948980d92da7e))


## v0.10.1 (2026-04-08)

### Bug Fixes

- Added photo_report_discipline to photo_reports
  ([`e967bf3`](https://github.com/cse120-ucm/S26-CSE-312/commit/e967bf3d61a1b2144306341cfdea9253f4d9e66b))

- Changed locking from incident table's status attribute to photo_report table's status attribute.
  Added confidence score column to photo_reports
  ([`10e921e`](https://github.com/cse120-ucm/S26-CSE-312/commit/10e921ea0e6d78dbbdaca37f184d543440bb6704))

- Connected processor to Gemini Embedding 2, successful vector db storage
  ([`9ede336`](https://github.com/cse120-ucm/S26-CSE-312/commit/9ede33634e6c0734795bad79936a19747fc29622))

- Included user_context in VLM inference call
  ([`2776962`](https://github.com/cse120-ucm/S26-CSE-312/commit/277696243ec86d32e67c633ae210da4942f8384d))

- Integrated processor.py with grouping logic, end to end connection complete
  ([`aa9ac5f`](https://github.com/cse120-ucm/S26-CSE-312/commit/aa9ac5fec4efe537fc0431cbfd3806d811e20d36))

- Minor inference prompt typo
  ([`426e9f4`](https://github.com/cse120-ucm/S26-CSE-312/commit/426e9f4e87392374c993dd9f092abb4f6566ed2b))

- Passing lint test
  ([`d4b9345`](https://github.com/cse120-ucm/S26-CSE-312/commit/d4b9345dfe069a4d59457da9e209ead44c476986))

- Passing test cases
  ([`b506263`](https://github.com/cse120-ucm/S26-CSE-312/commit/b5062631b203cd75db9ffac0771d2d0e174104c3))

- Prevented incident status (field status) from being set to "Completed" on creation
  ([`71c7517`](https://github.com/cse120-ucm/S26-CSE-312/commit/71c75170fa32320b73363c2a51136f744879e3ac))

- Removed linting errors
  ([`076d45e`](https://github.com/cse120-ucm/S26-CSE-312/commit/076d45e42f29b67b2d374f98f163319b6c47aec8))

- Test case changes
  ([`ad4fffc`](https://github.com/cse120-ucm/S26-CSE-312/commit/ad4fffc8d3cc824a707e81b848d546e54ce6bf77))

- Test typos
  ([`7d27b02`](https://github.com/cse120-ucm/S26-CSE-312/commit/7d27b02c6e2930908f1309f504ca2180e3da4f0b))

- Test update
  ([`e0f9fb8`](https://github.com/cse120-ucm/S26-CSE-312/commit/e0f9fb85fd0f8314c8548a3b6648610c29542ad4))

- Test update
  ([`c866166`](https://github.com/cse120-ucm/S26-CSE-312/commit/c86616665e21335c5c75fb7f48230f80e67bdb35))

- Test updates
  ([`343ac2c`](https://github.com/cse120-ucm/S26-CSE-312/commit/343ac2c3b3d00ec4070f885bf97b5aa114269090))


## v0.10.0 (2026-04-08)

### Bug Fixes

- Type lint errors in face blurring
  ([`7523444`](https://github.com/cse120-ucm/S26-CSE-312/commit/7523444e5da396a78e54df23499a07b544834917))

### Features

- **frontend**: Replace blazeface with mediapipe full_range and optimize blur bounds for backend VLM
  visibility
  ([`238037e`](https://github.com/cse120-ucm/S26-CSE-312/commit/238037e28f05cf71d15178d6d808b4f4a7ede269))


## v0.9.2 (2026-04-08)

### Bug Fixes

- Corrected typo
  ([`e176bbd`](https://github.com/cse120-ucm/S26-CSE-312/commit/e176bbd71746e6a95e30c6ea871c25e5be70cc81))

- Typo in test_persistance.py
  ([`d0de5bc`](https://github.com/cse120-ucm/S26-CSE-312/commit/d0de5bc5913b37138edb1d793e87d96272b93428))


## v0.9.1 (2026-04-07)

### Bug Fixes

- Multiple library call to JSON
  ([`98748a4`](https://github.com/cse120-ucm/S26-CSE-312/commit/98748a475adce9fb4e4ca2d085ae48af12159012))

- Update submission_id to test cases
  ([`01611b9`](https://github.com/cse120-ucm/S26-CSE-312/commit/01611b96b0acf61c4c862631c46386de6601c8f5))


## v0.9.0 (2026-04-07)

### Bug Fixes

- Verifying google creds + container db url
  ([`aac5ff1`](https://github.com/cse120-ucm/S26-CSE-312/commit/aac5ff1d66a3d33992822f763b40a1327f3e725f))

### Chores

- Organize image directories
  ([`52dc2d7`](https://github.com/cse120-ucm/S26-CSE-312/commit/52dc2d7f460b22c967b8c8d40ff4ddc808d3efb9))

- Removing old frontend + updating change logs
  ([`768b321`](https://github.com/cse120-ucm/S26-CSE-312/commit/768b3219e98aa42cf9f01ecba7c591e441f2b025))

### Refactoring

- Removing all instances of chat_with_media func
  ([`ffeb275`](https://github.com/cse120-ucm/S26-CSE-312/commit/ffeb275d364d162a0f5dc5759fdec4d766522fd8))


## v0.8.0 (2026-04-06)

### Refactoring

- Main rebase changes
  ([`c2eeec0`](https://github.com/cse120-ucm/S26-CSE-312/commit/c2eeec0b67497e33e9acc661d7d62973b2850550))


## v0.7.0 (2026-04-06)

### Bug Fixes

- Resolving test errors + compose url
  ([`28ad99e`](https://github.com/cse120-ucm/S26-CSE-312/commit/28ad99e5ef08b271deef3858b589896c611ec707))


## v0.6.0 (2026-04-02)

### Continuous Integration

- Update test.yml
  ([`f2af082`](https://github.com/cse120-ucm/S26-CSE-312/commit/f2af082514d8770032e8b4d8abdab22e502e8f2b))


## v0.5.0 (2026-04-02)

### Chores

- Removing duplicate assets
  ([`5905bb9`](https://github.com/cse120-ucm/S26-CSE-312/commit/5905bb950a4f906fe975942925b33086a2813f23))

### Features

- Setup isolated frontend, UI, and privacy blur
  ([`6f3c555`](https://github.com/cse120-ucm/S26-CSE-312/commit/6f3c5553ea35a0ec4c12ba4d806a7e337a7eec0e))

- Setup isolated frontend, UI, and privacy blur
  ([`eb7f423`](https://github.com/cse120-ucm/S26-CSE-312/commit/eb7f4236d0340409768f5634585bcfe0cd430b3c))

### Refactoring

- User landing page
  ([`959a6b9`](https://github.com/cse120-ucm/S26-CSE-312/commit/959a6b9fb9dc9ae3e2ab85358e937f7d7be594e9))


## v0.4.4 (2026-04-02)

### Bug Fixes

- Passing all linter error cases
  ([`e5a2e55`](https://github.com/cse120-ucm/S26-CSE-312/commit/e5a2e557c2003bf5b0baef241001166c8272a6cb))


## v0.4.3 (2026-03-31)

### Bug Fixes

- Changing elapsed time feature
  ([`b63285d`](https://github.com/cse120-ucm/S26-CSE-312/commit/b63285dc6d9b054a541b2795b8638aea2b146a74))

- Update page.tsx
  ([`fb15454`](https://github.com/cse120-ucm/S26-CSE-312/commit/fb154545f59194209b131214d498a4b5e1fc2e60))

### Chores

- Update page.tsx to call helper function
  ([`356e055`](https://github.com/cse120-ucm/S26-CSE-312/commit/356e055d733aa22cada06f4b63924dcb798f1d32))


## v0.4.2 (2026-03-31)

### Bug Fixes

- Update page.tsx
  ([`c251219`](https://github.com/cse120-ucm/S26-CSE-312/commit/c251219a3c6463190bbc2095a6f70ca70b3ecbfe))


## v0.4.1 (2026-03-31)

### Bug Fixes

- IMAGE_NAME build error
  ([`7cd8a1f`](https://github.com/cse120-ucm/S26-CSE-312/commit/7cd8a1ff465727992cb5157553ed67a1707cb231))

### Continuous Integration

- Updating github actions
  ([`24706fd`](https://github.com/cse120-ucm/S26-CSE-312/commit/24706fdd693998ad718124043791f7bd9455ce9f))


## v0.4.0 (2026-03-31)

### Bug Fixes

- Defer Gemini client setup until runtime
  ([`005969d`](https://github.com/cse120-ucm/S26-CSE-312/commit/005969dd6f349cdbb639580a9b5b45ce14ffad34))

- Silence mypy import for google generativeai
  ([`b1cc0cd`](https://github.com/cse120-ucm/S26-CSE-312/commit/b1cc0cdde4a943789e21d6b98b1f37606edef778))

### Features

- Wire Gemini Flash into processor scaffold
  ([`2fd8f09`](https://github.com/cse120-ucm/S26-CSE-312/commit/2fd8f094442700ba3b938c28265f741c289ec16e))


## v0.3.0 (2026-03-30)

### Bug Fixes

- Removing unnecessary disciplines
  ([`b182e23`](https://github.com/cse120-ucm/S26-CSE-312/commit/b182e23dd4af1f9213686e37f1a2850292e72bb7))

### Features

- Add structured model response parser for backend fields
  ([`36169d2`](https://github.com/cse120-ucm/S26-CSE-312/commit/36169d27d54a64df1b54283e290a8ef0467e0abb))


## v0.2.0 (2026-03-27)

### Features

- Add structured model response parser for backend fields
  ([`436940d`](https://github.com/cse120-ucm/S26-CSE-312/commit/436940df4633538a3400f8696829b046b8f0407a))


## v0.1.1 (2026-03-24)

### Bug Fixes

- Clean restructure: setup employee dashboard and backend integration
  ([`0b32c3f`](https://github.com/cse120-ucm/S26-CSE-312/commit/0b32c3fa92c16ca04d1afbca6baee18dd33d9241))

- Rebased feature/database into this branch
  ([`141f67e`](https://github.com/cse120-ucm/S26-CSE-312/commit/141f67e4d287e64161861c858387ef8f3d0d70f5))

- Refactor database table declarartions and inference params
  ([`8fbc3ce`](https://github.com/cse120-ucm/S26-CSE-312/commit/8fbc3ce28a54b46e3c061ded8efedeac29358635))

### Chores

- Align CI and tidy Python style
  ([`4933691`](https://github.com/cse120-ucm/S26-CSE-312/commit/493369163f399d7b9381e11eeb8787da362e0adf))

- Move backend into src/backend and tooling into tools
  ([`3483171`](https://github.com/cse120-ucm/S26-CSE-312/commit/34831717a7577bde4483f381723055faa1bf0483))

- Moving app/frontend to src/frontend for onboarding simplicity
  ([`dca08e3`](https://github.com/cse120-ucm/S26-CSE-312/commit/dca08e34e79d677ffad723300ccd21d7b4fc7853))

- Moving files from root to other directories
  ([`72a7772`](https://github.com/cse120-ucm/S26-CSE-312/commit/72a777214323af781fba5206d135f6a7f768bb0a))

- Redirecting dockerfile paths
  ([`7c75739`](https://github.com/cse120-ucm/S26-CSE-312/commit/7c75739ce536a07d2e148cae5dfac8ce26843b23))

- **deps**: Adding sqlalchemy to pyproject
  ([`d6b6a7d`](https://github.com/cse120-ucm/S26-CSE-312/commit/d6b6a7df1f42475ccd12642a51f51cabc8761b45))

- **deps**: Update python project + lockfile
  ([`b2de3f8`](https://github.com/cse120-ucm/S26-CSE-312/commit/b2de3f8d7eba6314b403ecbe4794330bae4cf005))

### Testing

- Adding new submission tests
  ([`927a118`](https://github.com/cse120-ucm/S26-CSE-312/commit/927a118895107ecb77e0b02591daa93ed7c01975))

- Fix tests after restructure
  ([`cda4655`](https://github.com/cse120-ucm/S26-CSE-312/commit/cda46551ec0dca5020b2ac081e5325890acf8bc3))


## v0.1.0 (2026-03-12)

- Initial Release
