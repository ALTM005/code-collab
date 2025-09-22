import { createSystem, defaultConfig } from "@chakra-ui/react";

const theme = createSystem(defaultConfig, {
  globalCss: {
    "*": {
      boxSizing: "border-box",
    },
    html: {
      height: "100%",
      backgroundColor: "#0f0a19", 
      color: "#f7fafc",            
    },
    body: {
      margin: 0,
      height: "100%",
      backgroundColor: "#0f0a19",
      color: "#f7fafc",
    },
  },
  theme: {
    ...defaultConfig.theme,
    tokens: {
      ...defaultConfig.theme?.tokens,
      colors: {
        ...defaultConfig.theme?.tokens?.colors,
        brand: {
          50: { value: "#e3f2f9" },
          500: { value: "#0078d4" },
          900: { value: "#003a75" },
        },
      },
    },
  },
});

export default theme;
