// src/components/HeroSectionApp.tsx
import React from "react";

const HeroSectionApp: React.FC = () => {
  return (
    <section className="hero" aria-labelledby="hero-title">
      <div className="circuit-background" aria-hidden="true">
        <svg className="circuit-svg" viewBox="0 0 1200 800" preserveAspectRatio="xMidYMid slice">
          <path className="circuit-path" d="M 0 200 L 300 200 L 350 250 L 600 250 L 650 200 L 1200 200" />
          <path className="circuit-path" d="M 0 400 L 200 400 L 250 350 L 500 350 L 550 400 L 1200 400" />
          <path className="circuit-path" d="M 0 600 L 400 600 L 450 550 L 700 550 L 750 600 L 1200 600" />
          <path className="circuit-path" d="M 200 0 L 200 300 L 250 350 L 250 500 L 200 550 L 200 800" />
          <path className="circuit-path" d="M 600 0 L 600 200 L 650 250 L 650 450 L 600 500 L 600 800" />
          <path className="circuit-path" d="M 1000 0 L 1000 400 L 950 450 L 950 650 L 1000 700 L 1000 800" />

          <circle className="circuit-node" cx="300" cy="200" r="4" />
          <circle className="circuit-node" cx="600" cy="250" r="4" />
          <circle className="circuit-node" cx="200" cy="400" r="4" />
          <circle className="circuit-node" cx="500" cy="350" r="4" />
          <circle className="circuit-node" cx="400" cy="600" r="4" />
          <circle className="circuit-node" cx="700" cy="550" r="4" />
          <circle className="circuit-node" cx="600" cy="200" r="4" />
          <circle className="circuit-node" cx="650" cy="450" r="4" />
          <circle className="circuit-node" cx="1000" cy="400" r="4" />
          <circle className="circuit-node" cx="950" cy="650" r="4" />
        </svg>
      </div>

      <div className="hero-container">
        <div className="hero-left">
          <div className="eyebrow reveal">
            <span className="eyebrow-accent" />
            MAi-RAG-PA Localized Private Interface
            <br />
            Memory-Augmented Intelligence · Retrieval-Augmented Generation · Personal Assistant
          </div>

          <h1 id="hero-title" className="reveal delay-1">
            <span className="highlight-text">Talk. Research. Recall. Schedule. Act.</span>
          </h1>
        </div>

        <div className="architecture-header reveal delay-5">
          <h2 className="architecture-title">
            <span className="highlight-text">An AI personal assistant that stays personal.</span>
          </h2>
          <div className="architecture-line" />
        </div>

        <div className="architecture-cards reveal delay-6">
          <div className="arch-card">
            <div className="card-header">
              <h3>Privacy Focused</h3>
            </div>
            <div className="layers-visual">
              <div className="layer-item">
                <div className="layer-indicator" />
                <span className="layer-label">Data sovereignty</span>
              </div>
              <div className="layer-item">
                <div className="layer-indicator" />
                <span className="layer-label">Everything runs locally</span>
              </div>
              <div className="layer-item">
                <div className="layer-indicator" />
                <span className="layer-label">No data leaves your computer</span>
              </div>
              <div className="layer-item">
                <div className="layer-indicator" />
                <span className="layer-label">Your data, your rules</span>
              </div>
            </div>
          </div>

          <div className="arch-card">
            <div className="card-header">
              <h3>Designed for Productivity</h3>
            </div>
            <div className="defense-visual">
              <div className="defense-item">
                <div className="defense-check">✓</div>
                <span>Voice capture and transcription</span>
              </div>
              <div className="defense-item">
                <div className="defense-check">✓</div>
                <span>File creation and editing</span>
              </div>
              <div className="defense-item">
                <div className="defense-check">✓</div>
                <span>Calendar planning and notifications</span>
              </div>
              <div className="defense-item">
                <div className="defense-check">✓</div>
                <span>Document research with citations</span>
              </div>
              <div className="defense-item">
                <div className="defense-check">✓</div>
                <span>Natural language database querying</span>
              </div>
            </div>
          </div>

          <div className="arch-card">
            <div className="card-header">
              <h3>Open Source and Free</h3>
            </div>
            <div className="layers-visual">
              <div className="layer-item">
                <div className="layer-indicator" />
                <span className="layer-label">No subscriptions</span>
              </div>
              <div className="layer-item">
                <div className="layer-indicator" />
                <span className="layer-label">No cloud dependency</span>
              </div>
              <div className="layer-item">
                <div className="layer-indicator" />
                <span className="layer-label">No compromises</span>
              </div>
              <div className="layer-item">
                <div className="layer-indicator" />
                <span className="layer-label">No personal data mining</span>
              </div>
            </div>
          </div>
        </div>

        <div className="architecture-header reveal delay-3">
          <h2 className="architecture-title">
            <span className="highlight-text">Built to stay focused. Built to stay accurate.</span>
          </h2>
          <div className="architecture-line" />
        </div>

        <div className="architecture-cards reveal delay-4">
          <div className="arch-card">
            <div className="card-header">
              <h3>Agentic Workflow</h3>
            </div>
            <div className="workflow-visual">
              <div className="workflow-step">
                <div className="step-indicator" />
                <span className="step-label">Generate</span>
              </div>
              <div className="workflow-connector" />
              <div className="workflow-step">
                <div className="step-indicator" />
                <span className="step-label">Verify</span>
              </div>
              <div className="workflow-connector" />
              <div className="workflow-step">
                <div className="step-indicator" />
                <span className="step-label">Fix</span>
              </div>
              <div className="workflow-connector" />
              <div className="workflow-step">
                <div className="step-indicator active" />
                <span className="step-label">Save</span>
              </div>
            </div>
            <p className="card-description">
              Multi-model flexibility gives you a broad choice of LLMs for different needs and hardware limits.
            </p>
            <p className="card-description">
              A structured pipeline validates outputs before documents are generated.
            </p>
            <p className="card-description">
              Strict protocols plus context, knowledge base, and workflow checks help produce grounded responses.
            </p>
          </div>

          <div className="arch-card">
            <div className="card-header">
              <h3>Triple-Layer Focus</h3>
            </div>
            <div className="layers-visual">
              <div className="layer-item">
                <div className="layer-indicator" />
                <span className="layer-label">System prompt</span>
              </div>
              <div className="layer-item">
                <div className="layer-indicator" />
                <span className="layer-label">Short-term memory</span>
              </div>
              <div className="layer-item">
                <div className="layer-indicator" />
                <span className="layer-label">Long-term memory</span>
              </div>
              <div className="layer-item">
                <div className="layer-indicator" />
                <span className="layer-label">Context-aware responses that remember your preferences and history</span>
              </div>
            </div>
          </div>

          <div className="arch-card">
            <div className="card-header">
              <h3>Hallucination Defense</h3>
            </div>
            <div className="defense-visual">
              <div className="defense-item">
                <div className="defense-check">✓</div>
                <span>Cross-references the knowledge base</span>
              </div>
              <div className="defense-item">
                <div className="defense-check">✓</div>
                <span>Admits uncertainty</span>
              </div>
              <div className="defense-item">
                <div className="defense-check">✓</div>
                <span>Verifies correctness</span>
              </div>
              <div className="defense-item">
                <div className="defense-check">✓</div>
                <span>Provides citations</span>
              </div>
              <div className="defense-item">
                <div className="defense-check">✓</div>
                <span>Avoids fabrications</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSectionApp;
