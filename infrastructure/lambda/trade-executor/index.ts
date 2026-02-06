import {
  SecretsManagerClient,
  GetSecretValueCommand,
} from '@aws-sdk/client-secrets-manager';
import { SSMClient, GetParameterCommand } from '@aws-sdk/client-ssm';
import { SNSClient, PublishCommand } from '@aws-sdk/client-sns';
import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';

// Hyperliquid SDK types (you'll need to install @hyperliquid/sdk or similar)
// For now, using a placeholder interface
interface HyperliquidClient {
  placeOrder(params: OrderParams): Promise<OrderResult>;
}

interface OrderParams {
  symbol: string;
  side: 'buy' | 'sell';
  size: number;
  price?: number;
  leverage?: number;
  stopLoss?: number;
  takeProfit?: number;
  reduceOnly?: boolean;
}

interface OrderResult {
  orderId: string;
  txHash: string;
  status: 'filled' | 'pending' | 'rejected';
  filledPrice?: number;
  filledSize?: number;
  error?: string;
}

// Environment variables
const SECRET_ARN = process.env.SECRET_ARN!;
const KILL_SWITCH_PARAM = process.env.KILL_SWITCH_PARAM!;
const SNS_TOPIC_ARN = process.env.SNS_TOPIC_ARN!;
const MAX_POSITION_USD = parseFloat(process.env.MAX_POSITION_USD || '2500');
const RATE_LIMIT_PER_MINUTE = parseInt(process.env.RATE_LIMIT_PER_MINUTE || '10');
const ENVIRONMENT = process.env.ENVIRONMENT || 'prod';

// Clients
const secretsManager = new SecretsManagerClient({});
const ssm = new SSMClient({});
const sns = new SNSClient({});

// In-memory rate limiting (resets on cold start, but Lambda concurrency helps)
const requestLog: Map<string, number[]> = new Map();

// Trade request schema
interface TradeRequest {
  action: 'buy' | 'sell' | 'long' | 'short' | 'close';
  symbol: string;
  size: number;
  price?: number;
  leverage?: number;
  stopLoss?: number;
  takeProfit?: number;
  requestId?: string;
}

// Processed request cache for idempotency
const processedRequests: Map<string, { result: any; timestamp: number }> = new Map();

export const handler = async (
  event: APIGatewayProxyEvent
): Promise<APIGatewayProxyResult> => {
  const startTime = Date.now();
  let tradeRequest: TradeRequest | null = null;

  try {
    // Parse request
    tradeRequest = JSON.parse(event.body || '{}') as TradeRequest;
    const sourceIp = event.requestContext.identity?.sourceIp || 'unknown';

    console.log(`[TRADE] Request from ${sourceIp}:`, {
      action: tradeRequest.action,
      symbol: tradeRequest.symbol,
      size: tradeRequest.size,
      requestId: tradeRequest.requestId,
      // Never log price/leverage details that could be used for front-running
    });

    // ========================================
    // VALIDATION 1: Kill Switch
    // ========================================
    const killSwitchEnabled = await checkKillSwitch();
    if (!killSwitchEnabled) {
      await sendNotification(
        `⛔ BLOCKED: Trading disabled by kill switch\n` +
          `Action: ${tradeRequest.action} ${tradeRequest.symbol}\n` +
          `Size: $${tradeRequest.size}`
      );
      return errorResponse(503, 'KILL_SWITCH_ACTIVE', 'Trading is disabled');
    }

    // ========================================
    // VALIDATION 2: Rate Limiting
    // ========================================
    const rateLimitOk = checkRateLimit(sourceIp);
    if (!rateLimitOk) {
      await sendNotification(
        `🚫 RATE LIMITED: Too many requests\n` +
          `IP: ${sourceIp}\n` +
          `Attempted: ${tradeRequest.action} ${tradeRequest.symbol}`
      );
      return errorResponse(429, 'RATE_LIMITED', 'Too many requests, slow down');
    }

    // ========================================
    // VALIDATION 3: Idempotency Check
    // ========================================
    if (tradeRequest.requestId) {
      const cached = processedRequests.get(tradeRequest.requestId);
      if (cached && Date.now() - cached.timestamp < 5 * 60 * 1000) {
        console.log(`[TRADE] Returning cached result for requestId: ${tradeRequest.requestId}`);
        return successResponse(cached.result);
      }
    }

    // ========================================
    // VALIDATION 4: Position Size
    // ========================================
    if (tradeRequest.size > MAX_POSITION_USD) {
      await sendNotification(
        `✗ REJECTED: Position size exceeds limit\n` +
          `Requested: $${tradeRequest.size}\n` +
          `Max allowed: $${MAX_POSITION_USD}\n` +
          `Action: ${tradeRequest.action} ${tradeRequest.symbol}`
      );
      return errorResponse(
        400,
        'POSITION_TOO_LARGE',
        `Position $${tradeRequest.size} exceeds limit of $${MAX_POSITION_USD}`
      );
    }

    // ========================================
    // VALIDATION 5: Symbol Validation
    // ========================================
    const validSymbols = ['BTC', 'ETH', 'SOL', 'ARB', 'AVAX', 'DOGE', 'LINK', 'OP', 'MATIC', 'APT'];
    if (!validSymbols.includes(tradeRequest.symbol.toUpperCase())) {
      await sendNotification(
        `✗ REJECTED: Invalid symbol\n` +
          `Symbol: ${tradeRequest.symbol}\n` +
          `Allowed: ${validSymbols.join(', ')}`
      );
      return errorResponse(400, 'INVALID_SYMBOL', `Symbol ${tradeRequest.symbol} not allowed`);
    }

    // ========================================
    // VALIDATION 6: Leverage Check
    // ========================================
    const maxLeverage = 10; // Conservative default
    if (tradeRequest.leverage && tradeRequest.leverage > maxLeverage) {
      await sendNotification(
        `✗ REJECTED: Leverage too high\n` +
          `Requested: ${tradeRequest.leverage}x\n` +
          `Max allowed: ${maxLeverage}x`
      );
      return errorResponse(
        400,
        'LEVERAGE_TOO_HIGH',
        `Leverage ${tradeRequest.leverage}x exceeds max of ${maxLeverage}x`
      );
    }

    // ========================================
    // EXECUTE TRADE
    // ========================================
    const privateKey = await getPrivateKey();
    const result = await executeTrade(privateKey, tradeRequest);

    // Clear private key from memory immediately
    // (In practice, the SDK may hold it; this is defense-in-depth)

    // ========================================
    // SEND SUCCESS NOTIFICATION
    // ========================================
    const emoji = result.status === 'filled' ? '✓' : '⏳';
    await sendNotification(
      `${emoji} ${tradeRequest.action.toUpperCase()} ${tradeRequest.symbol}\n` +
        `Size: $${tradeRequest.size}\n` +
        `Status: ${result.status}\n` +
        `${result.filledPrice ? `Price: $${result.filledPrice}` : ''}\n` +
        `TX: ${result.txHash?.slice(0, 16)}...`
    );

    // Cache result for idempotency
    if (tradeRequest.requestId) {
      processedRequests.set(tradeRequest.requestId, {
        result: result,
        timestamp: Date.now(),
      });
    }

    const duration = Date.now() - startTime;
    console.log(`[TRADE] Success in ${duration}ms:`, {
      orderId: result.orderId,
      status: result.status,
      txHash: result.txHash,
    });

    return successResponse({
      success: true,
      orderId: result.orderId,
      txHash: result.txHash,
      status: result.status,
      filledPrice: result.filledPrice,
      filledSize: result.filledSize,
    });
  } catch (error) {
    console.error('[TRADE] Error:', error);

    await sendNotification(
      `❌ TRADE ERROR\n` +
        `Action: ${tradeRequest?.action || 'unknown'} ${tradeRequest?.symbol || 'unknown'}\n` +
        `Error: ${error instanceof Error ? error.message : 'Unknown error'}`
    );

    return errorResponse(
      500,
      'EXECUTION_ERROR',
      error instanceof Error ? error.message : 'Trade execution failed'
    );
  }
};

// ========================================
// HELPER FUNCTIONS
// ========================================

async function checkKillSwitch(): Promise<boolean> {
  try {
    const response = await ssm.send(
      new GetParameterCommand({
        Name: KILL_SWITCH_PARAM,
      })
    );
    const value = response.Parameter?.Value?.toLowerCase();
    return value === 'true' || value === '1' || value === 'enabled';
  } catch (error) {
    console.error('[KILL_SWITCH] Error checking kill switch, defaulting to DISABLED:', error);
    // Fail closed - if we can't check the kill switch, don't trade
    return false;
  }
}

function checkRateLimit(sourceIp: string): boolean {
  const now = Date.now();
  const windowMs = 60 * 1000; // 1 minute window

  let timestamps = requestLog.get(sourceIp) || [];

  // Remove old timestamps
  timestamps = timestamps.filter((t) => now - t < windowMs);

  if (timestamps.length >= RATE_LIMIT_PER_MINUTE) {
    return false;
  }

  timestamps.push(now);
  requestLog.set(sourceIp, timestamps);
  return true;
}

async function getPrivateKey(): Promise<string> {
  const response = await secretsManager.send(
    new GetSecretValueCommand({
      SecretId: SECRET_ARN,
    })
  );

  if (!response.SecretString) {
    throw new Error('Private key not found in Secrets Manager');
  }

  return response.SecretString;
}

async function executeTrade(privateKey: string, request: TradeRequest): Promise<OrderResult> {
  // ========================================
  // HYPERLIQUID SDK INTEGRATION
  // ========================================
  // TODO: Replace with actual Hyperliquid SDK
  // Example with @hyperliquid/sdk:
  //
  // import { Hyperliquid } from '@hyperliquid/sdk';
  // const client = new Hyperliquid({ privateKey });
  //
  // const side = ['buy', 'long'].includes(request.action) ? 'buy' : 'sell';
  // const reduceOnly = request.action === 'close';
  //
  // return await client.placeOrder({
  //   symbol: request.symbol,
  //   side,
  //   size: request.size,
  //   price: request.price,
  //   leverage: request.leverage,
  //   stopLoss: request.stopLoss,
  //   takeProfit: request.takeProfit,
  //   reduceOnly,
  // });

  // Placeholder implementation for testing
  console.log('[TRADE] Would execute trade with Hyperliquid SDK');
  console.log('[TRADE] Private key length:', privateKey.length); // Never log the actual key

  // Simulate successful trade
  return {
    orderId: `ORD-${Date.now()}`,
    txHash: `0x${Math.random().toString(16).slice(2)}${Math.random().toString(16).slice(2)}`,
    status: 'filled',
    filledPrice: request.price || Math.random() * 10000,
    filledSize: request.size,
  };
}

async function sendNotification(message: string): Promise<void> {
  try {
    await sns.send(
      new PublishCommand({
        TopicArn: SNS_TOPIC_ARN,
        Message: message,
        Subject: 'OpenClaw Trade Alert',
      })
    );
  } catch (error) {
    console.error('[SNS] Failed to send notification:', error);
    // Don't throw - notification failure shouldn't block trade response
  }
}

function successResponse(data: any): APIGatewayProxyResult {
  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
      'X-Request-Id': data.orderId || 'unknown',
    },
    body: JSON.stringify(data),
  };
}

function errorResponse(
  statusCode: number,
  code: string,
  message: string
): APIGatewayProxyResult {
  return {
    statusCode,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      success: false,
      error: {
        code,
        message,
      },
    }),
  };
}
