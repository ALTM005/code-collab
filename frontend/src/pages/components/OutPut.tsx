import { Box, Text} from "@chakra-ui/react"

interface OutputProps{
    output: string;

}

const Output = ({output}:OutputProps) =>{
    return(
        <Box color="gray.500">
            
            <Box
            height="75vh"
            p={3}
            border="0px solid"
            borderRadius="md"
            borderColor="gray.600"
            fontFamily="monospace"
            whiteSpace="pre-wrap"
            overflowY="auto">
                {output? output : 'Click "Run Code" to see the output here.'}
            </Box>
        </Box>
    )
}

export default Output;