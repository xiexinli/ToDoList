/** live 测试凭证：来自 `eval "$(aws configure export-credentials --format env)"` 导出的临时凭证 */
import type { BedrockCredentials } from "@/adapters/llm.bedrock";

export function credsFromEnv(): BedrockCredentials {
  const { AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN } = process.env;
  if (!AWS_ACCESS_KEY_ID || !AWS_SECRET_ACCESS_KEY) {
    throw new Error('live: missing AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY — run: eval "$(aws configure export-credentials --format env)"');
  }
  return { accessKeyId: AWS_ACCESS_KEY_ID, secretAccessKey: AWS_SECRET_ACCESS_KEY, sessionToken: AWS_SESSION_TOKEN };
}
