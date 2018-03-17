class ResNeXtBottleNeck(nn.Module):
    def __init__(self, in_channels, intermediate, out_channels, stride, cardinality = 32):
        super(ResNeXtBottleNeck, self).__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels=in_channels, out_channels=intermediate, kernel_size=1, stride=1),
            nn.BatchNorm2d(intermediate),
            nn.ReLU(inplace=True)
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(in_channels=intermediate, out_channels=intermediate, groups=cardinality, kernel_size=3, stride=stride, padding=1),
            nn.BatchNorm2d(intermediate),
            nn.ReLU(inplace=True)
        )
        self.conv3 = nn.Sequential(
            nn.Conv2d(in_channels=intermediate, out_channels=out_channels, kernel_size=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
        self.relu = nn.ReLU(inplace=True)
        self.downsample = nn.Sequential(
            nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=1, stride=stride),
            nn.BatchNorm2d(out_channels)
        )

    def forward(self, x):
        identity = x
        identity = self.downsample(identity)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = x + identity
        x = self.relu(x)
        return(x)



class ResNeXt50(nn.Module):
    def __init__(self, num_classes):
        super(ResNeXt50, self).__init__()
        self.head = nn.Conv2d(in_channels=3, out_channels=64, kernel_size=7, padding=3, stride=2)
        self.bn = nn.BatchNorm2d(num_features=64)
        self.relu = nn.ReLU(inplace=True)
        self.pool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.group1 = self._make_group(ResNeXtBottleNeck, in_channels=64, intermediate=128, out_channels=256, blocks=3, stride=1)
        self.group2 = self._make_group(ResNeXtBottleNeck, in_channels=256, intermediate=256, out_channels=512, blocks=4, stride=2)
        self.group3 = self._make_group(ResNeXtBottleNeck, in_channels=512, intermediate=512, out_channels=1024, blocks=6, stride=2)
        self.group4 = self._make_group(ResNeXtBottleNeck, in_channels=1024, intermediate=1024, out_channels=2048, blocks=3, stride=2)
        self.avgpool = nn.AvgPool2d(kernel_size=7, stride=1)
        self.classifier = nn.Linear(in_features=2048, out_features=num_classes)
        self._initialize_weights()

    def forward(self, x):
        x = self.head(x)
        x = self.bn(x)
        x = self.relu(x)
        x = self.pool(x)
        x = self.group1(x)
        x = self.group2(x)
        x = self.group3(x)
        x = self.group4(x)
        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return(x)

    def _make_group(self, block, in_channels, intermediate, out_channels, blocks, stride):
        layers = []
        layers.append(block(in_channels=in_channels, intermediate=intermediate, out_channels=out_channels, stride=stride))
        stride = 1
        for i in range(blocks):
            layers.append(block(in_channels=out_channels, intermediate=intermediate, out_channels=out_channels, stride=stride))

        return(nn.Sequential(*layers))

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
                if m.bias is not None:
                    m.bias.data.zero_()
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()
            elif isinstance(m, nn.Linear):
                m.weight.data.normal_(0, 0.01)
                m.bias.data.zero_()
