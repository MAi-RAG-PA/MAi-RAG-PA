// src/contexts/InputTargetContext.tsx
import React, { createContext, useState, useContext, ReactNode } from 'react';

interface InputTargetContextType {
  target: string | null;
  setTarget: (target: string) => void;
}

const InputTargetContext = createContext<InputTargetContextType | undefined>(undefined);

export const InputTargetProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [target, setTarget] = useState<string | null>(null);

  return (
    <InputTargetContext.Provider value={{ target, setTarget }}>
      {children}
    </InputTargetContext.Provider>
  );
};

export const useInputTarget = (): InputTargetContextType => {
  const context = useContext(InputTargetContext);
  console.log('useInputTarget context:', context);
  if (!context) {
    console.error('useInputTarget called outside InputTargetProvider');
    throw new Error('useInputTarget must be used within an InputTargetProvider');
  }
  return context;
};
