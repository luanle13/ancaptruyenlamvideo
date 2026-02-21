# AnCapTruyenLamVideo Frontend

Angular frontend application for AnCapTruyenLamVideo.

## Tech Stack

- Angular 21+
- PrimeNG (UI Component Library)
- PrimeIcons
- PrimeFlex (CSS Utility Library)
- TypeScript

## Prerequisites

- Node.js 18+
- npm 9+
- Angular CLI (`npm install -g @angular/cli`)

## Installation

```bash
npm install
```

## Development Server

```bash
npm start
```

Navigate to `http://localhost:4200/`. The application will automatically reload if you change any source files.

## Build

```bash
npm run build
```

Build artifacts will be stored in the `dist/` directory.

## Running Tests

```bash
npm test
```

## Project Structure

```
src/
├── app/
│   ├── components/
│   │   ├── header/          # App header/navbar
│   │   └── stories/         # Stories CRUD component
│   ├── models/              # TypeScript interfaces
│   ├── services/            # API services
│   ├── app.config.ts        # App configuration
│   ├── app.routes.ts        # Route definitions
│   ├── app.ts               # Root component
│   └── app.html             # Root template
├── environments/            # Environment configs
└── styles.scss              # Global styles
```

## API Proxy

During development, the proxy configuration (`proxy.conf.json`) forwards `/api` requests to the backend server at `http://localhost:8000`.

## Further Help

For the full setup guide, refer to the main [README.md](../README.md) in the project root.
