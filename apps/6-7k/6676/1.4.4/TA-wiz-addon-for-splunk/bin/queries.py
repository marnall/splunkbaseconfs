ISSUES_QUERY = """
query IssuesTable($filterBy: IssueFilters, $first: Int, $after: String, $orderBy: IssueOrder) {
  issues: issuesV2(
    filterBy: $filterBy
    first: $first
    after: $after
    orderBy: $orderBy
  ) {
    nodes {
      id
      sourceRule {
        ... on Control {
          id
          name
          controlDescription: description
          resolutionRecommendation
          risks
          threats
        }
        ... on CloudEventRule {
          id
          name
          cloudEventRuleDescription: description
          sourceType
          type
          risks
          threats
        }
        ... on CloudConfigurationRule {
          id
          name
          cloudConfigurationRuleDescription: description
          remediationInstructions
          serviceType
          risks
        }
      }
      createdAt
      updatedAt
      resolvedAt
      statusChangedAt
      dueAt
      type
      projects {
        id
        name
        slug
        businessUnit
        riskProfile {
          businessImpact
        }
      }
      status
      severity
      threatDetectionDetails{
        eventOrigin
      }
      entitySnapshot {
        id
        type
        name
        status
        cloudPlatform
        region
        providerId
        nativeType
        subscriptionExternalId
        subscriptionName
        subscriptionTags
        resourceGroupExternalId
        cloudProviderURL
        tags
        createdAt
        externalId
      }
      notes {
        createdAt
        updatedAt
        text
        user {
          name
          email
        }
        serviceAccount {
          name
        }
      }
      serviceTickets {
        externalId
        name
        url
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

ISSUES_QUERY_WITH_SECURITY_FRAMEWORKS = """
query IssuesTable($filterBy: IssueFilters, $first: Int, $after: String, $orderBy: IssueOrder) {
  issues: issuesV2(
    filterBy: $filterBy
    first: $first
    after: $after
    orderBy: $orderBy
  ) {
    nodes {
      id
      sourceRule {
        __typename
        ... on Control {
          id
          name
          controlDescription: description
          resolutionRecommendation
          risks
          threats
          securitySubCategories {
            title
            id
            category {
              name
              id
              framework {
                id
                name
              }
            }
          }
        }
        ... on CloudEventRule {
          id
          name
          cloudEventRuleDescription: description
          sourceType
          type
          risks
          threats
        }
        ... on CloudConfigurationRule {
          id
          name
          cloudConfigurationRuleDescription: description
          remediationInstructions
          serviceType
          risks
          securitySubCategories {
            title
            id
            category {
              name
              id
              framework {
                id
                name
              }
            }
          }
        }
      }
      createdAt
      updatedAt
      dueAt
      type
      resolvedAt
      statusChangedAt
      projects {
        id
        name
        slug
        businessUnit
        riskProfile {
          businessImpact
        }
      }
      status
      severity
      threatDetectionDetails{
        eventOrigin
      }
      entitySnapshot {
        id
        type
        nativeType
        name
        status
        cloudPlatform
        cloudProviderURL
        providerId
        region
        resourceGroupExternalId
        subscriptionExternalId
        subscriptionName
        subscriptionTags
        tags
        createdAt
        externalId
      }
      serviceTickets {
        externalId
        name
        url
      }
      notes {
        createdAt
        updatedAt
        text
        user {
          name
          email
        }
        serviceAccount {
          name
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

VULNS_QUERY = """
query vulnerabilityFindings($first: Int, $after: String, $filterBy: VulnerabilityFindingFilters, $orderBy: VulnerabilityFindingOrder) {
  vulnerabilityFindings(
    first: $first
    after: $after
    filterBy: $filterBy
    orderBy: $orderBy
  ) {
    nodes {
      id
      portalUrl
      name
      CVEDescription
      fixDateDescription
      description
      CVSSSeverity
      hasExploit
      score
      exploitabilityScore
      impactScore
      hasCisaKevExploit
      vendorSeverity
      firstDetectedAt
      lastDetectedAt
      resolvedAt
      remediation
      locationPath
      detailedName
      version
      fixedVersion
      detectionMethod
      link
      status
      epssSeverity
      epssPercentile
      epssProbability
      validatedInRuntime
      layerMetadata {
        id
        details
        isBaseLayer
      }
      projects {
        name
        projectOwners{
          email
        }
      }
      relatedIssueAnalytics{
        criticalSeverityCount
        highSeverityCount
        mediumSeverityCount
        lowSeverityCount
        informationalSeverityCount
      }
      vulnerableAsset {
        ... on VulnerableAssetBase {
          id
          type
          name
          region
          providerUniqueId
          cloudProviderURL
          cloudPlatform
          status
          subscriptionExternalId
          subscriptionId
          subscriptionName
          tags
          hasLimitedInternetExposure
          hasWideInternetExposure
          isAccessibleFromVPN
          isAccessibleFromOtherVnets
          isAccessibleFromOtherSubscriptions
          scanSource
        }
        ... on VulnerableAssetVirtualMachine {
          operatingSystem
          ipAddresses
        }
        ... on VulnerableAssetContainerImage {
          imageId
        }
        ... on VulnerableAssetServerless {
          runtime
        }
        ... on VulnerableAssetContainer {
          ImageExternalId
          VmExternalId
          ServerlessContainer
          PodNamespace
          PodName
          NodeName
        }
        ... on VulnerableAssetRepositoryBranch {
          repositoryId
          repositoryName
          repositoryExternalId
        }
      }
    }
    pageInfo {
      endCursor
      hasNextPage
    }
  }
}
"""

AUDIT_LOGS_QUERY = """
    query AuditLogTable($first: Int, $after: String, $filterBy: AuditLogEntryFilters) {
  auditLogEntries(first: $first, after: $after, filterBy: $filterBy) {
    nodes {
      id
      action
      requestId
      status
      timestamp
      actionParameters
      userAgent
      sourceIP
      serviceAccount {
        id
        name
      }
      user {
        id
        name
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

DETECTIONS_QUERY = """
query Detections($filterBy: DetectionFilters, $first: Int, $after: String, $orderBy: DetectionOrder, $includeTriggeringEvents: Boolean = true) {
  detections(
    filterBy: $filterBy
    first: $first
    after: $after
    orderBy: $orderBy
    enforceTimestampContinuity: true
  ) {
    nodes {
      id
      issue {
        id
        url
      }
      ruleMatch {
        rule {
          id
          name
          sourceType
          securitySubCategories {
            title
            category {
              name
              framework {
                name
              }
            }
          }
        }
      }
      description
      severity
      createdAt
      cloudAccounts {
        cloudProvider
        externalId
        name
        linkedProjects {
          id
          name
        }
      }
      cloudOrganizations {
        cloudProvider
        externalId
        name
      }
      startedAt
      endedAt
      actors {
        id
        externalId
        name
        type
        nativeType
        actingAs {
          id
          externalId
          name
          type
          nativeType
        }
      }
      primaryActor {
        id
      }
      resources {
        id
        externalId
        name
        type
        nativeType
        region
        cloudAccount {
          cloudProvider
          externalId
          name
        }
        kubernetesNamespace {
          id
          providerUniqueId
          name
        }
        kubernetesCluster {
          id
          providerUniqueId
          name
        }
      }
      primaryResource {
        id
      }
      triggeringEvents(first: 10) @include(if: $includeTriggeringEvents) {
        nodes {
          ... on CloudEvent {
            id
            origin
            name
            description
            cloudProviderUrl
            cloudPlatform
            timestamp
            source
            category
            status
            actor {
              id
              actingAs {
                id
              }
            }
            actorIP
            actorIPMeta {
              country
              autonomousSystemNumber
              autonomousSystemOrganization
              reputation
              reputationDescription
              reputationSource
              relatedAttackGroupNames
              customIPRanges {
                id
                name
                isInternal
                ipRanges
              }
            }
            resources {
              id
            }
            extraDetails {
              ... on CloudEventRuntimeDetails {
                processTree {
                  command
                  container {
                    id
                    externalId
                    name
                    image {
                      id
                      externalId
                    }
                  }
                  path
                  hash
                  size
                  executionTime
                  runtimeProgramId
                  userId
                  userName
                }
              }
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""
