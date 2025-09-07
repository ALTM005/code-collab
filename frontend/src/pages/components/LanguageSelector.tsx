import { Box, Menu, Text, Portal, Button } from "@chakra-ui/react";
import { LANGUAGE_VERSIONS } from "../../constants";

type Language = keyof typeof LANGUAGE_VERSIONS;

interface LanguageSelectorProps {
  language: Language;
  onSelect: (language: Language) => void;
}


const languages = Object.entries(LANGUAGE_VERSIONS) as [Language, string][];

const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  language,
  onSelect,
}) => {
  return (
    <Box ml={2} mb={4}>
      <Text mb={2} fontSize="lg">
        Language:
      </Text>

      <Menu.Root>
        <Menu.Trigger asChild>
          <Button
            size="sm"
            bg="gray.800"
            color="gray.100"
            borderWidth="1px"
            borderColor="gray.700"
            _hover={{ bg: "gray.700", borderColor: "gray.600" }}
            _active={{ bg: "gray.700" }}
            _expanded={{ bg: "gray.700", borderColor: "gray.600" }}
            _focusVisible={{ outline: "none", boxShadow: "outline" }}
          >
            {language}
          </Button>
        </Menu.Trigger>

        <Portal>
          <Menu.Positioner>
            <Menu.Content
              bg="gray.800"
              color="gray.100"
              rounded="md"
              shadow="lg"
              minW="56"
              py="1"
              borderWidth="1px"
              borderColor="gray.700"
            >
              {languages.map(([lang, version]) => (
                <Menu.Item
                  key={lang}
                  value={lang}
                  onClick={() => onSelect(lang)}
                  bg={lang === language ? "gray.700" : "transparent"}
                  color={lang === language ? "blue.400" : "gray.300"}
                  _hover={{
                    color: "white",
                    bg: "gray.700",
                  }}
                  transition="background 0.1s ease-in, color 0.1s ease-in"
                >
                  {lang}
                  &nbsp;
                  <Text as="span" color="gray.500" fontSize="sm">
                    ({version})
                  </Text>
                </Menu.Item>
              ))}
            </Menu.Content>
          </Menu.Positioner>
        </Portal>
      </Menu.Root>
    </Box>
  );
};

export default LanguageSelector;
