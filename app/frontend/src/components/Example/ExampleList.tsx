import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "How to configure ultrawide monitor?",
    "How to get in touch with IT team?",
    "Where to find service helpdesk info?",
    "How to report a phishing attempt?",
    "How to establish VPN connection?",
    "What categories can you assist with?"
];

const GPT4V_EXAMPLES: string[] = [
    "How to configure ultrawide monitor?",
    "How to get in touch with IT team?",
    "Where to find service helpdesk info?",
    "How to report a phishing attempt?",
    "How to establish VPN connection?",
    "What categories can you assist with?"
];

interface Props {
    onExampleClicked: (value: string) => void;
    useGPT4V?: boolean;
}

export const ExampleList = ({ onExampleClicked, useGPT4V }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {(useGPT4V ? GPT4V_EXAMPLES : DEFAULT_EXAMPLES).map((question, i) => (
                <li key={i}>
                    <Example text={question} value={question} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
