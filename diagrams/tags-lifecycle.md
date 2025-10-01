# Tags Lifecycle in Cloud Governance

This diagram shows how tags are created, managed, and used throughout the cloud governance system across different scenarios.

```mermaid
flowchart TD
    %% Tag Creation Sources
    A[User/IAM Account] --> B[CSV File Import]
    A --> C[Manual Tag Input]
    A --> D[LDAP Directory]

    %% Tag Operations
    B --> E[tag_iam_user Policy]
    C --> F[tag_resources Policy]
    D --> G[tag_cluster Policy]
    C --> H[tag_non_cluster Policy]

    %% Tag Processing
    E --> I[IAM User Tagging]
    F --> J[Resource Tagging Engine]
    G --> K[Cluster Resource Tagging]
    H --> L[Non-Cluster Resource Tagging]

    %% Tag Application
    I --> M[User Tags Applied]
    J --> N[Mandatory Tags Applied]
    K --> O[Cluster Tags Applied]
    L --> P[Non-Cluster Tags Applied]

    %% Tag Usage in Policies
    M --> Q[Policy Evaluation Engine]
    N --> Q
    O --> Q
    P --> Q

    %% Tag-Based Decisions
    Q --> R{Check Skip Tags}
    R -->|Policy=notdelete| S[Skip Resource Action]
    R -->|skip=not_delete| S
    R -->|No Skip Tags| T[Continue Policy Execution]

    %% Policy Actions
    T --> U{Policy Type}
    U -->|Cleanup| V[Resource Cleanup]
    U -->|Monitoring| W[Resource Monitoring]
    U -->|Cost Management| X[Cost Analysis]

    %% Tag Lifecycle Management
    V --> Y[Update DaysCount Tag]
    W --> Z[Add Alert Tags]
    X --> AA[Add Cost Tags]

    %% Tag Scenarios
    subgraph "Tag Creation Scenarios"
        B1[CSV-based User Tagging]
        B2[CloudTrail-based Attribution]
        B3[Cluster Discovery Tagging]
        B4[Resource Launch Detection]
    end

    subgraph "Tag Exclusion Scenarios"
        C1[Policy=notdelete]
        C2[skip=not_delete]
        C3[FORCE_DELETE Override]
    end

    subgraph "Tag Operations"
        D1[Read - Generate CSV]
        D2[Update - Apply Tags]
        D3[Delete - Remove Tags]
    end

    %% Special Tag Flows
    BB[Resource Created] --> CC{Has Creator Info?}
    CC -->|Yes| DD[Extract User from CloudTrail]
    CC -->|No| EE[Apply NA Tags]
    DD --> FF[Lookup User in LDAP]
    FF -->|Found| GG[Apply User Tags]
    FF -->|Not Found| EE

    %% DaysCount Tag Logic
    HH[Policy Execution] --> II{dry_run mode?}
    II -->|yes| JJ[DaysCount = 0]
    II -->|no| KK{Existing DaysCount?}
    KK -->|No| LL[DaysCount = 1]
    KK -->|Yes| MM{Same Date?}
    MM -->|Yes| NN[Keep Current Count]
    MM -->|No| OO[Increment Count]

    %% Tag Validation
    PP[Tag Applied] --> QQ{Validate Tag}
    QQ -->|Valid| RR[Tag Persisted]
    QQ -->|Invalid| SS[Log Error]

    style S fill:#90EE90
    style T fill:#FFB6C1
    style C1 fill:#FFA07A
    style C2 fill:#FFA07A
    style GG fill:#87CEEB
    style EE fill:#DDA0DD
```

## Tag Lifecycle Scenarios

### 1. User and IAM Tagging (`tag_iam_user`)
- **Source**: CSV files with user data
- **Operations**: read/update/delete
- **Process**:
  - Read all users into CSV
  - Manual tag updates in CSV
  - Apply tags to IAM users
  - Sync with LDAP directory

### 2. Resource Tagging (`tag_resources`)
- **Source**: Mandatory tags configuration
- **Scope**: All cluster and non-cluster resources
- **Limitation**: Resources created in last 90 days
- **Process**:
  - Identify untagged resources
  - Apply mandatory tags
  - User attribution via CloudTrail

### 3. Cluster Resource Tagging (`tag_cluster`)
- **Source**: Cluster discovery and user input
- **Process**:
  - Scan security groups for cluster patterns
  - Find cluster stamp keys (e.g., `kubernetes.io/cluster/test-jlhpd`)
  - Apply cluster-specific tags
  - Merge with existing tags

### 4. Non-Cluster Resource Tagging (`tag_non_cluster`)
- **Source**: Instance names, CloudTrail, IAM user tags
- **Process**:
  - Extract username from launch time
  - Lookup user in LDAP
  - Apply user tags or NA tags
  - Update instance and associated resources

## Tag-Based Policy Exclusion

### Skip Mechanisms
- **`Policy=notdelete`**: Resource skipped from all cleanup actions
- **`skip=not_delete`**: Alternative skip tag format
- **Case Insensitive**: Tags normalized (remove `-`, `_`, uppercase)

### DaysCount Tag Logic
- **Dry Run Mode**: Always sets DaysCount = 0
- **Live Mode**: Increments counter daily
- **Format**: `date@count` (e.g., `2023-12-25@3`)
- **Action Trigger**: When count reaches `DAYS_TO_TAKE_ACTION`

## Tag Operations Flow

1. **Read Operation**: Generate CSV with current tags
2. **Update Operation**: Apply new tags from configuration
3. **Delete Operation**: Remove specified tags
4. **Validation**: Ensure tag compliance and format

## Integration Points

- **CloudTrail**: Resource creation attribution
- **LDAP**: User information lookup
- **IAM**: User tag synchronization
- **ElasticSearch**: Tag-based reporting
- **S3**: Tag data storage and backup
