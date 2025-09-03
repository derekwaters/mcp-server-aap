FROM ubi9/python-311:latest

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port if needed (optional, for HTTP server)
EXPOSE 8080

# Set environment variables (optional)
# ENV AAP_URL=your-aap-url
# ENV AAP_TOKEN=your-aap-token
# ENV AAP_PROJECT_ID=your-project-id

# Default command to run MCP server
CMD ["mcp-proxy", "python", "server.py", "--port", "8080", "--host", "0.0.0.0"]
