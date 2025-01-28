const axios = require("axios");

exports.handler = async (event) => {
  try {
    const body = JSON.parse(event.body);

    // Handle Slack URL verification
    if (body.type === "url_verification") {
      return {
        statusCode: 200,
        body: body.challenge,
      };
    }

    // Handle Slack interactive message
    if (body.type === "interactive_message") {
      const action = body.actions[0];
      const approvalStatus = action.value === "approve" ? "approved" : "declined";

      await axios.post(
        `https://api.github.com/repos/${process.env.REPO_OWNER}/${process.env.REPO_NAME}/dispatches`,
        {
          event_type: "slack-approval", // Updated to match the workflow event trigger
          client_payload: {
            approval_status: approvalStatus, // Include approval status in payload
          },
        },
        {
          headers: {
            Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
            "Content-Type": "application/json",
          }
        }
      );

      return {
        statusCode: 200,
        body: JSON.stringify({
          text: approvalStatus === "approved"
            ? "The cleanup workflow has been approved."
            : "The cleanup workflow has been declined."
        }),
      };
    }

    return {
      statusCode: 200,
      body: "No action taken.",
    };
  } catch (error) {
    console.error("Error:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: "Internal server error." }),
    };
  }
};