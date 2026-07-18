// src/utils/axeReporter.ts
import React from 'react';

const isDev = process.env.NODE_ENV === 'development';

if (isDev && typeof window !== 'undefined') {
  import('@axe-core/react').then((axe) => {
    axe.default(React, window, {
      rules: [
        { id: 'color-contrast', enabled: true },
        { id: 'aria-roles', enabled: true },
        { id: 'button-name', enabled: true }
      ]
    });
  });
}
