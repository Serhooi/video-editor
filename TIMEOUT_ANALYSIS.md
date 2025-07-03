# Remotion Lambda Timeout Analysis

## Problem
Render fails with "Render timeout - exceeded maximum wait time (5 minutes)"

## Key Findings from Official Documentation

### Two Types of Timeouts in Remotion Lambda:

1. **delayRender() timeout** 
   - Set via `timeoutInMilliseconds` in `renderMediaOnLambda()`
   - Set via `--timeout` when using CLI for rendering
   - Default: 30 seconds
   - Controls how long to wait for delayRender() calls

2. **Lambda function timeout**
   - Set via `--timeout` when deploying function with `npx remotion lambda functions deploy`
   - Set via `timeoutInSeconds` in `deployFunction()`
   - Default: 120 seconds (2 minutes)
   - Controls maximum execution time of Lambda function

## Root Cause
The Lambda function timeout (2 minutes default) is too short for video rendering, causing the main Lambda function to timeout before rendering completes.

## Solution
Need to increase the Lambda function timeout when deploying the function.

## Next Steps
1. Check current Lambda function configuration
2. Redeploy function with increased timeout
3. Update API code to use proper timeoutInMilliseconds



## Updated Analysis

### Default Values:
- **Lambda function timeout**: 120 seconds (2 minutes) 
- **delayRender() timeout**: 30 seconds (default)

### Current Issue:
Render fails after 5 minutes, which means:
1. Lambda function timeout is NOT the issue (would fail after 2 minutes)
2. The issue is likely with delayRender() timeout or polling timeout in our code

### Real Problem:
Our polling system has a 5-minute timeout (300 seconds / 60 attempts * 5 seconds = 5 minutes), but the actual render might need more time.

### Solution:
1. Increase `timeoutInMilliseconds` in renderMediaOnLambda() call
2. Increase polling timeout in our client code
3. Possibly increase Lambda function timeout for complex renders


## SOLUTION FOUND!

### Root Cause:
- **Default timeoutInMilliseconds**: 30 seconds (30000 ms)
- **Our current code**: Does NOT set timeoutInMilliseconds parameter
- **Result**: Render times out after 30 seconds, but our polling continues for 5 minutes

### Fix Required:
1. **In API code** (`/api/lambda/render/route.ts`):
   - Add `timeoutInMilliseconds: 600000` (10 minutes) to renderMediaOnLambda() call

2. **In client code** (`aws-api.ts`):
   - Increase polling timeout from 60 attempts to 120 attempts (10 minutes total)

### Implementation:
```typescript
// In renderMediaOnLambda call:
const result = await renderMediaOnLambda({
  // ... other params
  timeoutInMilliseconds: 600000, // 10 minutes
});

// In polling logic:
const maxAttempts = 120; // 10 minutes (120 * 5 seconds)
```

