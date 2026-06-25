// src/components/Hero.tsx
import React from 'react';

const Hero: React.FC = () => {
  return (
    <section className="hero">
      <div className="wrap hero-grid">
        <div className="hero-copy">
          <div className="eyebrow reveal">
            MAi-RAG-P.A. Localized Private Interface<br />
            (Memory-Augmented intelligence Retrieval-Augmented Generation Personal Assistant)
          </div>
          <h2 className="reveal delay-1">Talk. Research. Recall. Schedule. Act.</h2>
          <p className="reveal delay-2">
            Finally a Personal Assistant system where you are in control of your data, and Not the product!<br />
            Your Data Belongs to You, and best of all, <b>No Subscriptions!</b><br />
            The "entire" MAi-RAG Personal Assistant lives inside your computer, as does all of your personal content, Not on a cloud or on a server!<br />
            MAi-RAG Personal Assistant is a focused Web Browser User Interface for:<br />
            Voice Capture, Research, LLM Memory Tools, File Edit & Creation, Content Creation Planner/Calendar and Reminders, Draft Emails and Text Messages, System Prompt Controls all in one cohesive workspace.<br />
            Ingest <b>your</b> Documents into <b>your</b> system so that <b>your</b> localized Personal Assistant can access <b>your</b> various collections of designated knowledgebases that <b>you</b> customize.<br />
            These knowledgebases establish verifiable information for the LLM to generate information based on your preferences.<br />
            The MAi-RAG PersonalAssistant adapts and grows with you over time, based on what you ingest into it.
          </p>

          <div className="hero-meta reveal delay-4">
            <span><strong>Research Assistant</strong> Convergence of LLM Training & Long-term Memory that serves content selections as a combined knowledgebase.</span>
            <span><strong>Memory</strong> Persistent memory with Short-term and Long-Term Memory states.</span>
            <span><strong>Editor</strong> Text Editor right where you need it, to save ideas and keep everything in one place.</span>
            <span><strong>Calendar</strong> Your Planner for Events, Appointments. Reminders, etc. Get Notified of upcoming events.</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
