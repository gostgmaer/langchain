"""Usage examples and UI integration patterns for analytics APIs."""

# ============================================================================
# ANALYTICS API INTEGRATION GUIDE
# ============================================================================

"""
This document shows how to use the new analytics APIs to display token
consumption and costs in your UI.

The APIs provide multiple data formats to support different visualization
patterns:
- Overview reports (by provider, model, workflow, user)
- Time-series data (trends and historical)
- Individual request inspection (cost debugging)

All responses include comprehensive breakdowns for dashboard/reporting needs.
"""

# ============================================================================
# API ENDPOINTS
# ============================================================================

"""
GET /v1/analytics/tenant-overview
    Get comprehensive tenant usage overview

GET /v1/analytics/principal/{principal_id}
    Get usage for a specific user

GET /v1/analytics/time-series
    Get time-series metrics for trends

GET /v1/analytics/top-workflows
    Get most expensive workflows

GET /v1/analytics/expensive-requests
    Get individual high-cost requests
"""

# ============================================================================
# EXAMPLE 1: TENANT OVERVIEW DASHBOARD
# ============================================================================

"""
Frontend code to fetch and display tenant overview:

async function getTenantOverview() {
  const response = await fetch(
    '/v1/analytics/tenant-overview?start_date=2026-05-24T00:00:00&end_date=2026-05-31T23:59:59',
    {
      headers: {
        'x-tenant-id': 'tenant_123',
        'x-principal-id': 'user_456',
      }
    }
  );
  
  const overview = await response.json();
  
  // Display main metrics
  console.log('Total tokens:', overview.total_tokens.total_tokens);
  console.log('Total cost:', overview.total_cost.total_cost_usd);
  console.log('Success rate:', (overview.overall_success_rate * 100).toFixed(1) + '%');
  
  // Display by provider
  overview.by_provider.forEach(p => {
    console.log(`Provider: ${p.provider}`);
    console.log(`  Requests: ${p.request_count}`);
    console.log(`  Tokens: ${p.tokens.total_tokens}`);
    console.log(`  Cost: $${p.cost.total_cost_usd}`);
    console.log(`  Success: ${(p.success_rate * 100).toFixed(1)}%`);
  });
  
  // Display by model
  overview.by_model.forEach(m => {
    console.log(`Model: ${m.provider}/${m.model}`);
    console.log(`  Requests: ${m.request_count}`);
    console.log(`  Cost: $${m.cost.total_cost_usd}`);
  });
  
  // Display by workflow
  overview.by_workflow.forEach(w => {
    console.log(`Workflow: ${w.workflow}`);
    console.log(`  Requests: ${w.request_count}`);
    console.log(`  Cost: $${w.cost.total_cost_usd}`);
  });
  
  // Display by user
  overview.by_principal.forEach(p => {
    console.log(`User: ${p.principal_id}`);
    console.log(`  Requests: ${p.request_count}`);
    console.log(`  Cost: $${p.cost.total_cost_usd}`);
  });
}
"""

# ============================================================================
# EXAMPLE 2: USER-SPECIFIC USAGE REPORT
# ============================================================================

"""
Fetch usage for a specific user:

async function getUserUsage(principal_id) {
  const response = await fetch(
    `/v1/analytics/principal/${principal_id}?start_date=2026-05-24&end_date=2026-05-31`,
    {
      headers: {
        'x-tenant-id': 'tenant_123',
        'x-principal-id': 'admin_user',
      }
    }
  );
  
  const userUsage = await response.json();
  
  // Display user stats
  console.log(`User: ${principal_id}`);
  console.log(`Total requests: ${userUsage.total_request_count}`);
  console.log(`Total cost: $${userUsage.total_cost.total_cost_usd}`);
  console.log(`Total tokens: ${userUsage.total_tokens.total_tokens}`);
  
  // Show breakdown by provider
  const providers = userUsage.by_provider.reduce((acc, p) => {
    acc[p.provider] = p.cost.total_cost_usd;
    return acc;
  }, {});
  console.table(providers);
}
"""

# ============================================================================
# EXAMPLE 3: COST TRENDS (TIME-SERIES)
# ============================================================================

"""
Fetch daily cost trends for a chart:

async function getDailyCostTrends() {
  const response = await fetch(
    '/v1/analytics/time-series?bucket_hours=24&start_date=2026-05-01&end_date=2026-05-31',
    {
      headers: {
        'x-tenant-id': 'tenant_123',
        'x-principal-id': 'admin_user',
      }
    }
  );
  
  const timeSeries = await response.json();
  
  // Format for Chart.js or similar
  const labels = timeSeries.map(b => b.bucket_start.split('T')[0]);
  const costs = timeSeries.map(b => b.cost.total_cost_usd);
  const tokens = timeSeries.map(b => b.tokens.total_tokens);
  
  // Create chart
  const chartConfig = {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Daily Cost (USD)',
          data: costs,
          borderColor: 'rgb(255, 99, 132)',
          tension: 0.1
        },
        {
          label: 'Daily Tokens',
          data: tokens,
          borderColor: 'rgb(54, 162, 235)',
          tension: 0.1,
          yAxisID: 'y1'
        }
      ]
    }
  };
}
"""

# ============================================================================
# EXAMPLE 4: TOP WORKFLOWS BY COST
# ============================================================================

"""
Find which workflows are costing the most:

async function getTopWorkflows() {
  const response = await fetch(
    '/v1/analytics/top-workflows?limit=10&start_date=2026-05-24&end_date=2026-05-31',
    {
      headers: {
        'x-tenant-id': 'tenant_123',
        'x-principal-id': 'admin_user',
      }
    }
  );
  
  const workflows = await response.json();
  
  // Display in a table
  workflows.forEach(w => {
    console.log(`${w.workflow}`);
    console.log(`  Requests: ${w.request_count}`);
    console.log(`  Total Cost: $${w.cost.total_cost_usd}`);
    console.log(`  Avg Cost/Request: $${(w.cost.total_cost_usd / w.request_count).toFixed(4)}`);
    console.log(`  Tokens: ${w.tokens.total_tokens}`);
    console.log(`  Cost/1K Tokens: $${(w.cost.total_cost_usd / (w.tokens.total_tokens / 1000)).toFixed(6)}`);
  });
}
"""

# ============================================================================
# EXAMPLE 5: COST DEBUGGING - MOST EXPENSIVE REQUESTS
# ============================================================================

"""
Find individual high-cost requests for debugging:

async function getMostExpensiveRequests() {
  const response = await fetch(
    '/v1/analytics/expensive-requests?limit=20&start_date=2026-05-24&end_date=2026-05-31',
    {
      headers: {
        'x-tenant-id': 'tenant_123',
        'x-principal-id': 'admin_user',
      }
    }
  );
  
  const requests = await response.json();
  
  // Display top expensive requests
  requests.forEach(req => {
    console.log(`Trace: ${req.trace_id}`);
    console.log(`  Workflow: ${req.workflow}`);
    console.log(`  Provider/Model: ${req.provider}/${req.model}`);
    console.log(`  Tokens: ${req.tokens.prompt_tokens}(input) + ${req.tokens.completion_tokens}(output) = ${req.tokens.total_tokens}`);
    console.log(`  Cost: $${req.cost.total_cost_usd}`);
    console.log(`  Latency: ${req.latency_ms}ms`);
    console.log(`  User: ${req.principal_id}`);
  });
}
"""

# ============================================================================
# DASHBOARD LAYOUT SUGGESTIONS
# ============================================================================

"""
UI Dashboard could include:

1. TOP ROW - Key Metrics
   - Total Tokens (This Period)
   - Total Cost (This Period)
   - Average Cost Per Request
   - Success Rate (%)

2. CHARTS
   - Cost Trend (line chart over time)
   - Token Usage Trend (stacked area)
   - Cost by Provider (pie chart)
   - Cost by Workflow (horizontal bar)

3. TABLES
   - Top Workflows (sortable: cost, requests, tokens)
   - Top Models (sortable by cost)
   - Top Users (sortable by cost)
   - Most Expensive Requests (with trace links)

4. FILTERS
   - Date Range Picker (start/end dates)
   - User/Principal Filter
   - Provider Filter
   - Workflow Filter
   - Time Bucket Size (hourly, daily, weekly)

5. QUICK INSIGHTS
   - "Your most expensive workflow is X at $Y"
   - "Token usage increased by Z% since last period"
   - "Average token cost is $X per 1M"
"""

# ============================================================================
# RESPONSE DATA STRUCTURE REFERENCE
# ============================================================================

"""
TenantOverview response example:

{
  "tenant_id": "tenant_123",
  "time_period_start": "2026-05-24T00:00:00+00:00",
  "time_period_end": "2026-05-31T23:59:59+00:00",
  "total_request_count": 1542,
  "total_tokens": {
    "prompt_tokens": 156000,
    "completion_tokens": 89000,
    "total_tokens": 245000
  },
  "total_cost": {
    "total_cost_usd": "12.34"
  },
  "overall_success_rate": 0.987,
  "by_provider": [
    {
      "provider": "openai",
      "request_count": 600,
      "tokens": {
        "prompt_tokens": 80000,
        "completion_tokens": 45000,
        "total_tokens": 125000
      },
      "cost": {
        "total_cost_usd": "7.50"
      },
      "success_rate": 0.99,
      "avg_latency_ms": 234.5
    },
    {
      "provider": "ollama",
      "request_count": 942,
      "tokens": {
        "prompt_tokens": 76000,
        "completion_tokens": 44000,
        "total_tokens": 120000
      },
      "cost": {
        "total_cost_usd": "0.06"
      },
      "success_rate": 0.985,
      "avg_latency_ms": 156.2
    }
  ],
  "by_model": [
    {
      "model": "gpt-4o",
      "provider": "openai",
      "request_count": 400,
      "tokens": {...},
      "cost": {...},
      ...
    }
  ],
  "by_workflow": [
    {
      "workflow": "support_automation",
      "request_count": 800,
      "tokens": {...},
      "cost": {...},
      ...
    }
  ],
  "by_capability": [
    {
      "capability": "generate",
      "request_count": 1200,
      "tokens": {...},
      "cost": {...},
      ...
    }
  ],
  "by_principal": [
    {
      "principal_id": "user_123",
      "request_count": 400,
      "tokens": {...},
      "cost": {...},
      ...
    }
  ]
}
"""

# ============================================================================
# PERFORMANCE NOTES
# ============================================================================

"""
Performance Considerations:

1. The database uses indexes on:
   - (tenant_id, created_at)
   - (workflow_run_id, created_at)
   - (provider, model)
   - Time-bucketed partitions on created_at

2. All queries filter by (tenant_id, created_at) for optimal index usage.

3. Time range defaults to 7 days if not specified - use this for most
   UI displays to keep response times under 500ms.

4. For longer periods (30+ days), use aggregation endpoints or reduce
   limit parameters.

5. Consider caching daily aggregations for historical periods that
   won't change.
"""

# ============================================================================
# INTEGRATION CHECKLIST
# ============================================================================

"""
When integrating into your UI:

☐ Add analytics module imports to app/analytics/__init__.py
☐ Register analytics router in app/bootstrap.py (DONE)
☐ Add x-tenant-id, x-principal-id headers to all requests
☐ Implement date pickers for time range selection
☐ Create dashboard components for:
  - Key metrics summary
  - Cost trend chart
  - Breakdown tables (provider, model, workflow, user)
  - Top workflows table
  - Expensive requests list
☐ Add filters for date range, user, provider, workflow
☐ Implement caching for response data (consider Redis)
☐ Add error handling for API failures
☐ Test with different time ranges and user segments
☐ Monitor API response times (target: <500ms)
☐ Document for end users
"""
