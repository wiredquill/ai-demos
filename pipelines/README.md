# Open WebUI Response Level Pipeline

This pipeline automatically cycles through different response complexity levels for the SUSE AI Demo. It demonstrates how the same question can be answered at different complexity levels, making it perfect for educational and testing scenarios.

## 🎯 Purpose

The Response Level Pipeline modifies user messages to request responses at different complexity levels:

1. **Default**: No modification - standard response
2. **Kid Mode (5-year-old)**: Simple explanations with fun examples
3. **Young Scientist (12-year-old)**: Age-appropriate science details
4. **College Student**: Technical context with examples  
5. **Scientific**: Full technical detail and precise terminology

## 🔄 Cycling Behavior

The pipeline automatically cycles through all levels:
- **Message 1**: Default level
- **Message 2**: Kid Mode 
- **Message 3**: Young Scientist
- **Message 4**: College Student
- **Message 5**: Scientific
- **Message 6**: Back to Default (cycle repeats)

## 🚀 Installation

This pipeline is automatically deployed with the SUSE AI Demo Helm charts. No manual configuration required.

### Manual Installation (if needed)

1. Copy `response_level_pipeline.py` to your Open WebUI pipelines directory
2. Restart Open WebUI to load the pipeline
3. The pipeline will be automatically available

## ⚙️ Configuration

### Environment Variables

- `PIPELINE_MODE`: 
  - `auto-cycle` (default): Automatically cycles through levels
  - `manual`: Allows manual level selection
- `LOG_LEVEL`: Logging level (default: INFO)

### Pipeline Modes

#### Auto-Cycle Mode (Default)
```bash
PIPELINE_MODE=auto-cycle
```
- Automatically advances to next level after each message
- Perfect for automated testing and demonstrations
- Used by the automation system

#### Manual Mode
```bash
PIPELINE_MODE=manual
```
- Stays on selected level until manually changed
- Better for interactive use when you want consistent level

## 📊 Example Usage

### Input Message
```
"How do rockets work?"
```

### Pipeline Processing by Level

**Level 1 - Default:**
```
"How do rockets work?"
```

**Level 2 - Kid Mode:**
```
"How do rockets work? Explain like I'm 5 years old using simple words, fun examples, and easy-to-understand concepts."
```

**Level 3 - Young Scientist:**
```
"How do rockets work? Explain like I'm 12 years old with some science details but keep it understandable and engaging."
```

**Level 4 - College Student:**
```
"How do rockets work? Explain like I'm a college student with technical context, examples, and deeper analysis."
```

**Level 5 - Scientific:**
```
"How do rockets work? Give me the full scientific explanation with precise terminology, detailed mechanisms, and technical accuracy."
```

## 🔧 Integration with SUSE AI Demo

This pipeline integrates seamlessly with the existing automation system:

- **Automation Testing**: Each automation cycle tests a different response level
- **Provider Comparison**: Compare how different AI providers handle complexity levels
- **Educational Demo**: Show AI adaptability to different audiences
- **Performance Testing**: Validate response quality across complexity levels

## 📝 Logs and Monitoring

The pipeline logs all processing actions:

```
INFO - Response Level Pipeline initialized in auto-cycle mode
INFO - Available levels: ['Default', 'Kid Mode', 'Young Scientist', 'College Student', 'Scientific']
INFO - Processing message with level: Kid Mode
INFO - Original message: How do rockets work?...
INFO - Modified message: How do rockets work? Explain like I'm 5 years old using simple words...
INFO - Next level will be: Young Scientist
```

## 🧪 Testing

Run the pipeline in test mode:

```bash
cd pipelines
python response_level_pipeline.py
```

This will cycle through all levels with a test message and show the results.

## 🔄 Version Compatibility

- **Open WebUI**: 0.5.0+
- **Pipeline API**: Compatible with Open WebUI Pipelines 0.5.0
- **Python**: 3.8+

## 🐛 Troubleshooting

### Pipeline Not Loading
- Check Open WebUI logs for pipeline loading errors
- Verify pipeline file permissions
- Ensure Open WebUI has pipelines feature enabled

### Cycling Not Working
- Check `PIPELINE_MODE` environment variable
- Verify pipeline logs for cycling messages
- Restart Open WebUI if needed

### No Message Modification
- Check pipeline logs for processing messages
- Verify pipeline is active in Open WebUI
- Test with debug logging enabled

## 📈 Future Enhancements

Potential additions to this pipeline:
- **Language Level Pipeline**: Different languages
- **Domain-Specific Pipeline**: Medical, legal, technical domains
- **Tone Pipeline**: Formal, casual, humorous responses
- **Length Pipeline**: Brief, detailed, comprehensive responses