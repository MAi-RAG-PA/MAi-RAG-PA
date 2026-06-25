// src/TestContext.tsx
import React from 'react';
import { useInputTarget, InputTargetProvider } from "./InputTargetContext";

const TestComponent = () => {
  const { target, setTarget } = useInputTarget();
  return (
    <div>
      <p>Target: {target}</p>
      <button onClick={() => setTarget('test')}>Set Target</button>
    </div>
  );
};

export const TestApp = () => (
  <InputTargetProvider>
    <TestComponent />
  </InputTargetProvider>
);
