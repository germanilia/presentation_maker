import AddIcon from '@mui/icons-material/Add';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import CancelIcon from '@mui/icons-material/Cancel';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import {
  Box,
  Button,
  Container,
  FormControl,
  IconButton,
  InputLabel,
  List,
  ListItem,
  ListItemIcon,
  ListItemSecondaryAction,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography
} from '@mui/material';
import CircularProgress from '@mui/material/CircularProgress';
import axios from 'axios';
import React, { useEffect, useState } from 'react';
import { DragDropContext, Draggable } from 'react-beautiful-dnd';
import { ChromePicker } from 'react-color';
import { StrictModeDroppable } from './StrictModeDroppable';

const predefinedThemes = {
  default: {
    colors: {
      title: { r: 102, g: 45, b: 145 },
      text: { r: 33, g: 33, b: 33 },
      bullet: { r: 102, g: 45, b: 145 },
      table: {
        header: { r: 102, g: 45, b: 145 },
        text: { r: 33, g: 33, b: 33 }
      },
      footer: { r: 128, g: 128, b: 128 }
    }
  },
  light: {
    colors: {
      title: { r: 33, g: 33, b: 33 },
      text: { r: 66, g: 66, b: 66 },
      bullet: { r: 3, g: 169, b: 244 },
      table: {
        header: { r: 3, g: 169, b: 244 },
        text: { r: 66, g: 66, b: 66 }
      },
      footer: { r: 158, g: 158, b: 158 }
    }
  },
  blueWhite: {
    colors: {
      title: { r: 25, g: 118, b: 210 },
      text: { r: 33, g: 33, b: 33 },
      bullet: { r: 25, g: 118, b: 210 },
      table: {
        header: { r: 25, g: 118, b: 210 },
        text: { r: 33, g: 33, b: 33 }
      },
      footer: { r: 97, g: 97, b: 97 }
    }
  },
  nature: {
    colors: {
      title: { r: 56, g: 142, b: 60 },
      text: { r: 33, g: 33, b: 33 },
      bullet: { r: 76, g: 175, b: 80 },
      table: {
        header: { r: 56, g: 142, b: 60 },
        text: { r: 33, g: 33, b: 33 }
      },
      footer: { r: 158, g: 158, b: 158 }
    }
  }
};

// Create an axios instance with default configuration
const api = axios.create({
  baseURL: 'http://localhost:9090',
  headers: {
    'Content-Type': 'application/json',
  }
});

function App() {
  const [config, setConfig] = useState({
    theme: {
      colors: {
        title: { r: 102, g: 45, b: 145 },
        text: { r: 0, g: 0, b: 0 },
        bullet: { r: 102, g: 45, b: 145 },
        table: {
          header: { r: 102, g: 45, b: 145 },
          text: { r: 0, g: 0, b: 0 }
        },
        footer: { r: 128, g: 128, b: 128 }
      },
      fonts: {
        title: { name: 'Arial', size: 32 },
        text: { name: 'Arial', size: 18 },
        table: { name: 'Arial', size: 16 },
        footer: { name: 'Arial', size: 12 }
      },
      footer: ''
    },
    topic: '',
    general_instructions: '',
    sub_topics: [],
    logo_base64: '',
    logo_description: '',
    output_path: 'output',
    search_source: 'serper'
  });

  const [colorPickerOpen, setColorPickerOpen] = useState({});
  const [newSubTopic, setNewSubTopic] = useState('');
  const [editingIndex, setEditingIndex] = useState(-1);
  const [editingText, setEditingText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [fileExists, setFileExists] = useState(false);
  // eslint-disable-next-line no-unused-vars
  const [downloadReady, setDownloadReady] = useState(false);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const response = await api.get('/api/load-config');
        setConfig(response.data);
      } catch (error) {
        console.error('Error loading config:', error);
      }
    };
    loadConfig();
  }, []);

  useEffect(() => {
    const checkFile = async (folder) => {
      try {
        const response = await api.get(`/api/check-file/${folder}/presentation.pptx`, {
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
          },
        });
        setFileExists(response.data.exists);
        return response.data.exists;
      } catch (error) {
        console.error('Error checking file:', error);
        setFileExists(false);
        return false;
      }
    };

    // Check immediately
    checkFile(config.output_path);

    // Set up periodic checking
    const interval = setInterval(() => checkFile(config.output_path), 9090);
    return () => clearInterval(interval);
  }, [config.output_path]);

  const handleColorChange = (color, path) => {
    const newConfig = { ...config };
    const pathArray = path.split('.');
    let current = newConfig;
    
    for (let i = 0; i < pathArray.length - 1; i++) {
      current = current[pathArray[i]];
    }
    
    current[pathArray[pathArray.length - 1]] = {
      r: color.rgb.r,
      g: color.rgb.g,
      b: color.rgb.b
    };
    
    setConfig(newConfig);
  };

  const handleLogoUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        // Store both the base64 data and the file name
        setConfig({
          ...config,
          logo_base64: reader.result,
          logo_description: file.name
        });

        // Preview the image (optional)
        const img = document.createElement('img');
        img.src = reader.result;
        img.onload = () => {
          // You can add image validation here if needed
          console.log('Logo loaded successfully:', file.name);
        };
      };
      reader.onerror = () => {
        console.error('Error reading file');
        alert('Error reading logo file');
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemoveLogo = () => {
    setConfig({
      ...config,
      logo_base64: '',
      logo_description: ''
    });
  };

  const handleAddSubTopic = () => {
    if (newSubTopic.trim()) {
      setConfig({
        ...config,
        sub_topics: [...config.sub_topics, newSubTopic.trim()]
      });
      setNewSubTopic('');
    }
  };

  const handleRemoveSubTopic = (index) => {
    const newSubTopics = config.sub_topics.filter((_, i) => i !== index);
    setConfig({ ...config, sub_topics: newSubTopics });
  };

  const handleDragEnd = (result) => {
    if (!result.destination) return;

    const items = Array.from(config.sub_topics);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);

    setConfig({
      ...config,
      sub_topics: items
    });
  };

  const handleGenerate = async () => {
    try {
      setIsGenerating(true);
      setDownloadReady(false);
      
      // First save the configuration
      await api.post('/api/save-config', config);
      
      // Then trigger the generation with the current config
      const response = await api.post('/api/generate', { config });
      
      if (response.data.status === 'success') {
        setDownloadReady(true);
        alert('Presentation generated successfully!');
      } else {
        throw new Error(response.data.message || 'Unknown error occurred');
      }
    } catch (error) {
      console.error('Error generating presentation:', error);
      alert(error.response?.data?.message || error.message || 'Error generating presentation');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = async () => {
    try {
      const response = await api.get(`/api/download/presentation.pptx`, {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'presentation.pptx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      if (error.response?.status === 404) {
        alert('No presentation file available for download');
      } else {
        alert('Error downloading file');
      }
    }
  };

  const handleStartEdit = (index, topic) => {
    setEditingIndex(index);
    setEditingText(topic);
  };

  const handleSaveEdit = (index) => {
    if (editingText.trim()) {
      const newSubTopics = [...config.sub_topics];
      newSubTopics[index] = editingText.trim();
      setConfig({
        ...config,
        sub_topics: newSubTopics
      });
    }
    setEditingIndex(-1);
    setEditingText('');
  };

  const handleCancelEdit = () => {
    setEditingIndex(-1);
    setEditingText('');
  };

  const handleEditKeyPress = (e, index) => {
    if (e.key === 'Enter') {
      handleSaveEdit(index);
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  const handleThemeChange = (themeName) => {
    setConfig({
      ...config,
      theme: {
        ...config.theme,
        colors: predefinedThemes[themeName].colors
      }
    });
  };

  const ColorPickerButton = ({ color, path, label }) => (
    <Box mb={2}>
      <Typography variant="subtitle2">{label}</Typography>
      <Box
        onClick={() => setColorPickerOpen({ ...colorPickerOpen, [path]: !colorPickerOpen[path] })}
        sx={{
          width: 100,
          height: 30,
          backgroundColor: `rgb(${color.r},${color.g},${color.b})`,
          cursor: 'pointer',
          border: '1px solid #ccc',
          borderRadius: 1
        }}
      />
      {colorPickerOpen[path] && (
        <Box position="absolute" zIndex="tooltip">
          <Box position="fixed" top={0} right={0} bottom={0} left={0} onClick={() => setColorPickerOpen({ ...colorPickerOpen, [path]: false })} />
          <ChromePicker
            color={{ r: color.r, g: color.g, b: color.b }}
            onChange={(color) => handleColorChange(color, path)}
          />
        </Box>
      )}
    </Box>
  );

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>Presentation Configuration</Typography>
        
        <Box mb={3}>
          <TextField
            fullWidth
            label="Topic"
            value={config.topic}
            onChange={(e) => setConfig({ ...config, topic: e.target.value })}
          />
        </Box>

        <Box mb={3}>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="General Instructions"
            value={config.general_instructions}
            onChange={(e) => setConfig({ ...config, general_instructions: e.target.value })}
          />
        </Box>

        <Box mb={3}>
          <Typography variant="h6" gutterBottom>Theme Colors</Typography>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Select Theme</InputLabel>
            <Select
              label="Select Theme"
              onChange={(e) => handleThemeChange(e.target.value)}
              defaultValue="default"
            >
              <MenuItem value="default">Default Purple</MenuItem>
              <MenuItem value="light">Light Blue</MenuItem>
              <MenuItem value="blueWhite">Blue and White</MenuItem>
              <MenuItem value="nature">Nature Green</MenuItem>
            </Select>
          </FormControl>
          <Box display="flex" gap={2} flexWrap="wrap">
            <ColorPickerButton color={config.theme.colors.title} path="theme.colors.title" label="Title Color" />
            <ColorPickerButton color={config.theme.colors.text} path="theme.colors.text" label="Text Color" />
            <ColorPickerButton color={config.theme.colors.bullet} path="theme.colors.bullet" label="Bullet Color" />
            <ColorPickerButton color={config.theme.colors.table.header} path="theme.colors.table.header" label="Table Header Color" />
            <ColorPickerButton color={config.theme.colors.footer} path="theme.colors.footer" label="Footer Color" />
          </Box>
        </Box>

        <Box mb={3}>
          <Typography variant="h6" gutterBottom>Sub Topics</Typography>
          <Box display="flex" gap={1} mb={2}>
            <TextField
              fullWidth
              label="New Sub Topic"
              value={newSubTopic}
              onChange={(e) => setNewSubTopic(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleAddSubTopic();
                }
              }}
            />
            <IconButton color="primary" onClick={handleAddSubTopic}>
              <AddIcon />
            </IconButton>
          </Box>
          <DragDropContext onDragEnd={handleDragEnd}>
            <StrictModeDroppable droppableId="sub-topics">
              {(provided) => (
                <List {...provided.droppableProps} ref={provided.innerRef}>
                  {config.sub_topics.map((topic, index) => (
                    <Draggable key={`topic-${index}`} draggableId={`topic-${index}`} index={index}>
                      {(provided, snapshot) => (
                        <ListItem
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          sx={{
                            bgcolor: snapshot.isDragging ? 'action.hover' : 'transparent',
                            '& .drag-handle, & .edit-button': {
                              opacity: 0,
                              transition: 'opacity 0.2s'
                            },
                            '&:hover .drag-handle, &:hover .edit-button': {
                              opacity: 1
                            },
                            position: 'relative',
                            '& .MuiListItemSecondaryAction-root': {
                              right: 8,
                              display: 'flex',
                              alignItems: 'center'
                            }
                          }}
                        >
                          <ListItemIcon {...provided.dragHandleProps}>
                            <DragIndicatorIcon className="drag-handle" />
                          </ListItemIcon>
                          {editingIndex === index ? (
                            <TextField
                              fullWidth
                              value={editingText}
                              onChange={(e) => setEditingText(e.target.value)}
                              onKeyDown={(e) => handleEditKeyPress(e, index)}
                              autoFocus
                              size="small"
                              sx={{ mr: 8 }} // Make room for action buttons
                            />
                          ) : (
                            <ListItemText 
                              primary={topic}
                              sx={{ pr: 8 }} // Make room for action buttons
                            />
                          )}
                          <ListItemSecondaryAction>
                            {editingIndex === index ? (
                              <>
                                <IconButton 
                                  edge="end" 
                                  onClick={() => handleSaveEdit(index)}
                                  sx={{ mr: 1 }}
                                >
                                  <SaveIcon />
                                </IconButton>
                                <IconButton 
                                  edge="end" 
                                  onClick={handleCancelEdit}
                                >
                                  <CancelIcon />
                                </IconButton>
                              </>
                            ) : (
                              <>
                                <IconButton 
                                  edge="end" 
                                  onClick={() => handleStartEdit(index, topic)}
                                  className="edit-button"
                                  sx={{ mr: 1 }}
                                >
                                  <EditIcon />
                                </IconButton>
                                <IconButton 
                                  edge="end" 
                                  onClick={() => handleRemoveSubTopic(index)}
                                >
                                  <DeleteIcon />
                                </IconButton>
                              </>
                            )}
                          </ListItemSecondaryAction>
                        </ListItem>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </List>
              )}
            </StrictModeDroppable>
          </DragDropContext>
        </Box>

        <Box mb={3}>
          <Typography variant="h6" gutterBottom>Logo</Typography>
          <Box display="flex" alignItems="center" gap={2}>
            <input
              accept="image/*"
              style={{ display: 'none' }}
              id="logo-upload"
              type="file"
              onChange={handleLogoUpload}
            />
            <label htmlFor="logo-upload">
              <Button variant="contained" component="span">
                Upload Logo
              </Button>
            </label>
            {config.logo_base64 && (
              <>
                <Box
                  component="img"
                  src={config.logo_base64}
                  alt="Logo preview"
                  sx={{
                    height: 40,
                    width: 'auto',
                    objectFit: 'contain'
                  }}
                />
                <IconButton 
                  color="error" 
                  onClick={handleRemoveLogo}
                  size="small"
                >
                  <DeleteIcon />
                </IconButton>
                <Typography variant="body2" color="textSecondary">
                  {config.logo_description}
                </Typography>
              </>
            )}
          </Box>
        </Box>

        <Box mb={3}>
          <Typography variant="h6" gutterBottom>Footer Text</Typography>
          <TextField
            fullWidth
            label="Footer Text"
            value={config.theme.footer}
            onChange={(e) => setConfig({
              ...config,
              theme: {
                ...config.theme,
                footer: e.target.value
              }
            })}
            helperText="Enter the text to appear in the footer of each slide"
          />
        </Box>

        <Box mb={3}>
          <FormControl fullWidth>
            <InputLabel>Search Source</InputLabel>
            <Select
              // value={config.search_source}
              label="Search Source"
              onChange={(e) => setConfig({ ...config, search_source: e.target.value })}
              defaultValue="serper"
            >
              <MenuItem value="youtube">YouTube</MenuItem>
              <MenuItem value="serper">Web Search (Serper)</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <Box display="flex" gap={2}>
          <Button
            variant="contained"
            color="primary"
            size="large"
            onClick={handleGenerate}
            fullWidth
            disabled={isGenerating}
            startIcon={isGenerating ? <CircularProgress size={20} color="inherit" /> : <AutoFixHighIcon />}
          >
            {isGenerating ? 'Generating...' : 'Generate Presentation'}
          </Button>
          
          <Button
            variant="contained"
            color="secondary"
            size="large"
            onClick={handleDownload}
            startIcon={<DownloadIcon />}
            disabled={!fileExists || isGenerating}
          >
            Download
          </Button>
        </Box>
      </Paper>
    </Container>
  );
}

export default App; 